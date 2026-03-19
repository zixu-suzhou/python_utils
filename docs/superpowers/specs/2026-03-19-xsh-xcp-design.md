# xsh / xcp — SSH/SCP Wrapper Tool Design

**Date:** 2026-03-19
**Status:** Approved
**Python version:** 3.8+

## Problem

Connecting to remote test devices requires complex commands with ProxyJump, repeated password entry, and verbose syntax. Goal: simple `xsh bench01` and `xcp file bench01:/path` commands that handle passwords and jump hosts transparently.

## Config File

Location: `~/.config/xsh/hosts.yaml` (permissions 600, manually edited).
The tool verifies permissions at load time and prints a warning if the file is world- or group-readable.

```yaml
jumphosts:
  jmp1:
    host: 10.190.161.169
    user: env1szh
    password: "jumphost_password"
    port: 22               # optional, default 22

servers:
  bench01:
    host: 10.178.235.54
    user: root
    port: 22               # optional, default 22
    # no password → key-based auth; no jump → direct connection

  zeekr:
    host: 198.18.36.1
    user: root
    password: "ENGVV202410$"
    jump: jmp1             # references a jumphost by name
```

Fields:
- `jumphosts`: named jump host definitions (host, user, password, port)
- `servers`: named target servers (host, user, password, port, jump)
- `password` is optional — omit for key-based auth (no sshpass wrapper)
- `jump` is optional — omit for direct connections

## Command Usage

```bash
# Interactive SSH login
xsh zeekr
xsh bench01

# Run a command remotely
xsh zeekr "ls /map/hdz2szh/"

# Pass ssh flags before server name
xsh -v zeekr
xsh -o StrictHostKeyChecking=no bench01

# SCP upload (all scp flags like -r, -P are passed through)
xcp -r output/examples/ zeekr:/map/hdz2szh/output/
xcp file.txt bench01:/tmp/

# SCP download
xcp zeekr:/map/hdz2szh/log.txt ./
xcp -r bench01:/data/ ./local_data/
```

Unknown server names (not in config) fall back to system `ssh`/`scp` transparently.
If any remote token in an `xcp` call is unknown, the **entire command falls back** to system `scp`.

## sshpass Command Construction

Passwords are passed via a temporary file (`sshpass -f TMPFILE`) rather than `-p PASSWORD` to avoid exposure in `/proc/<pid>/cmdline`. The temp file is created with mode 600.

**Temp file lifecycle:** Use `subprocess.run()` (not `os.execvp`) when passwords are involved, wrapped in `try/finally` to delete the temp file after the child process exits. Exit Python with the child's return code via `sys.exit(result.returncode)`. When no passwords are needed (key auth, no sshpass), use `os.execvp()` for a clean process replacement.

This is an accepted trade-off for password-auth-only test devices.

All four target × jump combinations:

### 1. Direct, no password (key auth)
```
ssh [-p PORT] [ssh_flags] USER@HOST [remote_cmd]
```

### 2. Direct, with password
```
sshpass -f /tmp/xsh_XXXX ssh [-p PORT] [ssh_flags] USER@HOST [remote_cmd]
```

### 3. Jump host, no target password (key auth to target, password to jump)
```
ssh \
  -o "ProxyCommand=sshpass -f /tmp/xsh_XXXX ssh -W %h:%p [-p JUMP_PORT] JUMP_USER@JUMP_HOST" \
  [-p PORT] [ssh_flags] USER@HOST [remote_cmd]
```

### 4. Jump host, both passwords
```
sshpass -f /tmp/xsh_XXXX ssh \
  -o "ProxyCommand=sshpass -f /tmp/xsh_YYYY ssh -W %h:%p [-p JUMP_PORT] JUMP_USER@JUMP_HOST" \
  [-p PORT] [ssh_flags] USER@HOST [remote_cmd]
```

**SCP equivalents** — same four combinations, replacing `ssh USER@HOST [remote_cmd]` with:
```
scp [scp_flags] SRC DST
```
where `SRC`/`DST` are the rewritten paths (e.g. `root@198.18.36.1:/remote/path`).
Note: `ssh` uses `-p PORT` (lowercase); `scp` uses `-P PORT` (uppercase). The ProxyCommand inner ssh always uses `-p`.

Full SCP example with jump + both passwords:
```
sshpass -f /tmp/xsh_XXXX scp \
  -o "ProxyCommand=sshpass -f /tmp/xsh_YYYY ssh -W %h:%p [-p JUMP_PORT] JUMP_USER@JUMP_HOST" \
  [-P PORT] [scp_flags] SRC DST
```

## Implementation

### Files

```
python_utils/
├── xsh.py          # xsh entry point
├── xcp.py          # xcp entry point
├── xsh_config.py   # shared config loading and ServerInfo resolution
└── install.sh      # creates symlinks in ~/.local/bin

~/.config/xsh/
└── hosts.yaml

~/.local/bin/
├── xsh -> .../python_utils/xsh.py   (symlink, chmod +x)
└── xcp -> .../python_utils/xcp.py   (symlink, chmod +x)
```

### xsh_config.py

Returns a `ServerInfo` dataclass (or `None` for unknown names):

```python
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class JumpInfo:
    host: str
    user: str
    password: Optional[str] = None   # None = key auth
    port: int = 22

@dataclass
class ServerInfo:
    host: str
    user: str
    password: Optional[str] = None   # None = key auth
    port: int = 22
    jump: Optional[JumpInfo] = None
```

Responsibilities:
- Load and parse `~/.config/xsh/hosts.yaml`
- Check file permissions; warn if not 600
- Resolve server name → `ServerInfo` (or `None` if not found)

### xsh.py

Argument parsing:
- Scan argv left to right; skip flags (tokens starting with `-`) and their values
- First non-flag token is the server name
- Remaining tokens after server name are the remote command
- Flags before the server name are collected as `ssh_flags` and passed through

Logic:
- Look up server name → `ServerInfo`
- If `None`: `os.execvp("ssh", ["ssh"] + original_argv[1:])`
- If found and **no passwords needed** (key auth, no jump): `os.execvp("ssh", cmd)`
- If found and **passwords involved**: write temp file(s), `subprocess.run(cmd)` in `try/finally` that deletes temp file(s), `sys.exit(result.returncode)`

### xcp.py

Remote token detection rule:
- A token is treated as remote if it contains `:` AND the substring before the first `:` contains no `/` and does not start with `.`
- This matches `bench01:/path` but not `./log:data` or `/tmp/file:backup`

Argument parsing:
- Collect flags (tokens starting with `-`) and non-flag tokens separately
- Apply remote detection to non-flag tokens
- Extract server name (part before `:`) from remote tokens

Logic:
- Look up each detected server name in config
- If **any** server name is unknown (or zero remote tokens): `os.execvp("scp", ["scp"] + original_argv[1:])`
- If all known and **no passwords needed**: `os.execvp("scp", cmd)`
- If all known and **passwords involved**: write temp file(s), `subprocess.run(cmd)` in `try/finally` that deletes temp file(s), `sys.exit(result.returncode)`

### Error Handling
- Config file missing: print message with example config path and exit 1
- `sshpass` not installed but needed: print `sudo apt install sshpass` and exit 1
- YAML parse error: show file path and error line, exit 1
- Unknown `jump` reference in config: print error with the offending server name, exit 1

## install.sh

1. Check `sshpass` is installed; print `sudo apt install sshpass` hint if not (non-fatal)
2. Create `~/.local/bin/` if missing
3. Symlink with `ln -sf` (overwrites stale symlinks): `xsh.py` → `~/.local/bin/xsh`, `xcp.py` → `~/.local/bin/xcp`
4. `chmod +x` both source scripts
5. Check if `~/.local/bin` is in `$PATH`; if not, print reminder to add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc`
6. Create `~/.config/xsh/hosts.yaml` with example content if it does not exist; set permissions to 600
