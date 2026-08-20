#!/bin/bash
# Mount a Bosch DFS/UNC path via CIFS.
# Usage: ./cifs_mount_unc.sh <unc-path> <username> <mount_point>
# Example:
#   ./cifs_mount_unc.sh '\\abtvdfs2.de.bosch.com\ismdfs\loc\szh\DA\Parking' hdz2szh /mnt/Parking
#
# Note: a DFS path like the example above is a link that redirects to a real
# server share (here \\szh-soc4.apac.bosch.com\urmszh_i_2006_014$). The kernel
# cifs client follows the referral itself; if that fails, pass the resolved
# target directly. Resolve it manually with:
#   smbclient //abtvdfs2.de.bosch.com/ismdfs -N -c 'cd loc\szh\DA\Parking; ls'
# and read the "Unable to follow dfs referral [...]" line.
#
# Requires: sudo apt install cifs-utils smbclient

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <unc-path> <username> <mount_point>"
    echo "Example: $0 '\\\\abtvdfs2.de.bosch.com\\ismdfs\\loc\\szh\\DA\\Parking' hdz2szh /mnt/Parking"
    exit 1
fi

UNC_PATH="$1"
USERNAME="$2"
MOUNT_POINT="$3"

# \\server\share\sub\dir  ->  //server/share/sub/dir
SHARE_PATH="${UNC_PATH//\\//}"

if [[ ! -d "$MOUNT_POINT" ]]; then
    echo "Creating mount point: $MOUNT_POINT"
    sudo mkdir -p "$MOUNT_POINT"
fi

echo "Mounting $SHARE_PATH -> $MOUNT_POINT"
sudo mount -t cifs "$SHARE_PATH" "$MOUNT_POINT" \
    -o username="$USERNAME",workgroup=APAC,vers=3.1.1,uid="$(id -u)",gid="$(id -g)"

echo "Done. Mounted at $MOUNT_POINT"
