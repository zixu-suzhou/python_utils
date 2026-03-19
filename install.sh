#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/xsh"
CONFIG_FILE="$CONFIG_DIR/hosts.yaml"

echo "=== xsh/xcp installer ==="

# Check sshpass
if ! command -v sshpass &>/dev/null; then
    echo "WARNING: sshpass not installed. You will need it for password-auth servers."
    echo "  Install with: sudo apt install sshpass"
fi

# Create ~/.local/bin if needed
mkdir -p "$BIN_DIR"

# Symlink with -sf to overwrite stale symlinks
ln -sf "$SCRIPT_DIR/xsh.py" "$BIN_DIR/xsh"
ln -sf "$SCRIPT_DIR/xcp.py" "$BIN_DIR/xcp"
chmod +x "$SCRIPT_DIR/xsh.py" "$SCRIPT_DIR/xcp.py"
echo "Installed: $BIN_DIR/xsh -> $SCRIPT_DIR/xsh.py"
echo "Installed: $BIN_DIR/xcp -> $SCRIPT_DIR/xcp.py"

# Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "NOTE: $BIN_DIR is not in your PATH."
    echo "Add this to ~/.bashrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Scaffold config if missing
if [[ ! -f "$CONFIG_FILE" ]]; then
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_FILE" <<'YAML'
# xsh/xcp server configuration

jumphosts:
  jmp1:
    host: 10.190.161.169
    user: env1szh
    password: "your_jump_password"
    port: 22          # optional, default 22

servers:
  # Example: server via jump host with password auth
  zeekr:
    host: 198.18.36.1
    user: root
    password: "your_target_password"
    jump: jmp1

  # Example: direct server with key-based auth (no password)
  bench01:
    host: 10.178.235.54
    user: root
    port: 22
YAML
    chmod 600 "$CONFIG_FILE"
    echo ""
    echo "Created example config: $CONFIG_FILE"
    echo "Edit it to add your servers and passwords."
else
    echo "Config already exists: $CONFIG_FILE (not overwritten)"
fi

echo ""
echo "Done! Try: xsh bench01"
