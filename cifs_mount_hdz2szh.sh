#!/bin/bash
# Usage: ./cifs_mount_hdz2szh.sh <username> <mount_point>
# Example: ./cifs_mount_hdz2szh.sh hdz2szh /mnt/hdz2szh
# please install sudo apt install cifs-utils first
# Real server: \\SGP0FS70.APAC.BOSCH.COM\HDZ2SZH$ (personal home share)

set -euo pipefail

SHARE_PATH="//SGP0FS70.APAC.BOSCH.COM/HDZ2SZH$"

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <username> <mount_point>"
    echo "Example: $0 hdz2szh /mnt/hdz2szh"
    exit 1
fi

USERNAME="$1"
MOUNT_POINT="$2"

if [[ ! -d "$MOUNT_POINT" ]]; then
    echo "Creating mount point: $MOUNT_POINT"
    sudo mkdir -p "$MOUNT_POINT"
fi

echo "Mounting $SHARE_PATH -> $MOUNT_POINT"
sudo mount -t cifs "$SHARE_PATH" "$MOUNT_POINT" \
    -o username="$USERNAME",workgroup=APAC,vers=3.1.1,uid="$(id -u)",gid="$(id -g)"

echo "Done. Mounted at $MOUNT_POINT"
