#!/usr/bin/env python3
"""xcp — SCP wrapper with automatic password and jump-host handling."""

import os
import sys
import subprocess
from typing import List, Tuple

from xsh_config import load_config, resolve_server, ServerInfo
from xsh import _write_temp_password, _build_proxy_command, _check_sshpass

# Flags that consume the next argument
_SCP_OPTION_FLAGS = {"-F", "-i", "-J", "-l", "-o", "-P", "-S"}


def is_remote_token(token: str) -> bool:
    """Return True if token looks like server:/path (not a local path with colon)."""
    if ":" not in token:
        return False
    prefix = token.split(":")[0]
    return "/" not in prefix and not prefix.startswith(".")


def parse_xcp_args(
    argv: List[str],
) -> Tuple[List[str], List[str], List[Tuple[str, str, str]]]:
    """Parse xcp arguments.

    Returns (scp_flags, local_tokens, remote_tokens).
    remote_tokens is a list of (server_name, remote_path, original_token).
    """
    scp_flags = []
    local_tokens = []
    remote_tokens = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("-"):
            scp_flags.append(token)
            if token in _SCP_OPTION_FLAGS and i + 1 < len(argv):
                i += 1
                scp_flags.append(argv[i])
        elif is_remote_token(token):
            server, _, path = token.partition(":")
            remote_tokens.append((server, path, token))
        else:
            local_tokens.append(token)
        i += 1

    return scp_flags, local_tokens, remote_tokens


def _extract_positional(argv: List[str]) -> List[str]:
    """Extract positional (non-flag) tokens from argv, preserving their original order."""
    positional = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("-"):
            if token in _SCP_OPTION_FLAGS and i + 1 < len(argv):
                i += 1  # skip the option's value argument
        else:
            positional.append(token)
        i += 1
    return positional


def _exec_scp(server_map, scp_flags, argv):
    """Build and exec the scp command with rewrites for known servers."""
    # Pick any server for the connection params (upload or download, one jump config)
    server_name = next(iter(server_map))
    info = server_map[server_name]

    temp_files = []
    try:
        target_tmp = None
        jump_tmp = None

        if info.password:
            target_tmp = _write_temp_password(info.password)
            temp_files.append(target_tmp)

        if info.jump and info.jump.password:
            jump_tmp = _write_temp_password(info.jump.password)
            temp_files.append(jump_tmp)

        cmd = []
        if target_tmp:
            cmd += ["sshpass", "-f", target_tmp]
        cmd += ["scp"]

        if info.jump:
            proxy = _build_proxy_command(info.jump, jump_tmp)
            cmd += [
                "-o", f"ProxyCommand={proxy}",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
            ]

        if info.port != 22:
            cmd += ["-P", str(info.port)]

        cmd += scp_flags

        # Rewrite remote tokens: server:/path → user@host:/path
        for token in argv:
            if is_remote_token(token):
                srv, _, path = token.partition(":")
                if srv in server_map:
                    s = server_map[srv]
                    cmd.append(f"{s.user}@{s.host}:{path}")
                else:
                    cmd.append(token)
            else:
                cmd.append(token)

        if not temp_files:
            os.execvp(cmd[0], cmd)
            return

        _check_sshpass()
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    finally:
        for f in temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


def main():
    scp_flags, local_tokens, remote_tokens = parse_xcp_args(sys.argv[1:])

    if not remote_tokens:
        # No remote tokens → fall back to system scp
        os.execvp("scp", ["scp"] + sys.argv[1:])
        return

    cfg = load_config()
    server_map = {}
    for server_name, _, _ in remote_tokens:
        info = resolve_server(server_name, cfg)
        if info is None:
            # Any unknown server → full fallback
            os.execvp("scp", ["scp"] + sys.argv[1:])
            return
        server_map[server_name] = info

    # Preserve original positional argument order so that downloads (remote first,
    # local last) are not silently reversed into uploads.
    positional_argv = _extract_positional(sys.argv[1:])
    _exec_scp(server_map, scp_flags, positional_argv)


if __name__ == "__main__":
    main()
