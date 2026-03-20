#!/bin/bash
# Usage: ./mount_cifs.sh <username> <mount_point>
# Example: ./mount_cifs.sh dnb1szh /mnt/fvp
# please install sudo apt install cifs-utils first
# Real server: \\szh0fs07.APAC.BOSCH.COM\xccn_2409_165$

set -euo pipefail

SHARE_PATH="//szh0fs07.APAC.BOSCH.COM/xccn_2409_165$"

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <username> <mount_point>"
    echo "Example: $0 dnb1szh /mnt/fvp"
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
