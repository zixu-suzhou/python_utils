#!/usr/bin/env python3
"""xsh — SSH wrapper with automatic password and jump-host handling."""

import os
import sys
import shutil
import tempfile
import subprocess
from typing import List, Optional, Tuple

from xsh_config import load_config, resolve_server, ServerInfo, JumpInfo

# Flags that consume the next argument (not a server name)
_SSH_OPTION_FLAGS = {
    "-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J",
    "-L", "-l", "-m", "-o", "-p", "-Q", "-R", "-S", "-W", "-w",
}


def parse_xsh_args(argv: List[str]) -> Tuple[List[str], str, List[str]]:
    """Parse xsh arguments.

    Returns (ssh_flags, server_name, remote_cmd).
    Exits if no server name is provided.
    """
    ssh_flags = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("-"):
            ssh_flags.append(token)
            if token in _SSH_OPTION_FLAGS and i + 1 < len(argv):
                i += 1
                ssh_flags.append(argv[i])
        else:
            server_name = token
            remote_cmd = argv[i + 1:]
            return ssh_flags, server_name, remote_cmd
        i += 1

    print("xsh: no server name provided\nUsage: xsh [ssh-flags] <server> [command]",
          file=sys.stderr)
    sys.exit(1)


def main():
    ssh_flags, server_name, remote_cmd = parse_xsh_args(sys.argv[1:])
    cfg = load_config()
    info = resolve_server(server_name, cfg)

    if info is None:
        os.execvp("ssh", ["ssh"] + sys.argv[1:])
        return  # unreachable

    _exec_ssh(info, ssh_flags, remote_cmd)


def _write_temp_password(password: str) -> str:
    fd, path = tempfile.mkstemp(prefix="xsh_")
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(password)
    return path


def _build_proxy_command(jump: JumpInfo, jump_tmp: Optional[str]) -> str:
    inner = []
    if jump_tmp:
        inner += ["sshpass", "-f", jump_tmp]
    inner += ["ssh", "-W", "%h:%p"]
    if jump.port != 22:
        inner += ["-p", str(jump.port)]
    inner.append(f"{jump.user}@{jump.host}")
    return " ".join(inner)


def _exec_ssh(info: ServerInfo, ssh_flags: List[str], remote_cmd: List[str]):
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
        cmd += ["ssh"]

        if info.jump:
            proxy = _build_proxy_command(info.jump, jump_tmp)
            cmd += ["-o", f"ProxyCommand={proxy}"]

        if info.port != 22:
            cmd += ["-p", str(info.port)]

        cmd += ssh_flags
        cmd.append(f"{info.user}@{info.host}")
        cmd += remote_cmd

        if not temp_files:
            os.execvp(cmd[0], cmd)
            return  # unreachable

        _check_sshpass()
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    finally:
        for f in temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


def _check_sshpass():
    if not shutil.which("sshpass"):
        print("xsh: sshpass not found. Install with: sudo apt install sshpass",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
