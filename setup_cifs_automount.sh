#!/bin/bash
# Configure persistent (systemd automount) CIFS mounts for 03_Exchange and Parking.
#
# Usage: sudo ./setup_cifs_automount.sh [username]     (default: current user)
#
# Creates /etc/cifs-<user>.cred (mode 600, root-owned) and adds fstab entries with
# x-systemd.automount, so the shares are mounted lazily on first access instead of
# blocking boot when the network isn't up yet.
#
# Idempotent: re-running replaces the managed fstab block and rewrites the password.
# Re-run this after changing your domain password.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Must run as root: sudo $0 $*" >&2
    exit 1
fi

USERNAME="${1:-${SUDO_USER:-$(id -un)}}"
CRED_FILE="/etc/cifs-${USERNAME}.cred"
MARKER="# >>> cifs automount (managed by setup_cifs_automount.sh) >>>"
MARKER_END="# <<< cifs automount <<<"

UID_N="$(id -u "$USERNAME")"
GID_N="$(id -g "$USERNAME")"

# share|mountpoint
SHARES=(
    '//szh0fs07.APAC.BOSCH.COM/xccn_2409_165$|/mnt/03_Exchange'
    '//szh-soc4.apac.bosch.com/urmszh_i_2006_014$|/mnt/Parking'
)

read -rsp "Domain password for APAC\\${USERNAME}: " PASSWORD
echo

echo "Writing $CRED_FILE"
umask 077
cat > "$CRED_FILE" <<CRED
username=${USERNAME}
domain=APAC
password=${PASSWORD}
CRED
chown root:root "$CRED_FILE"
chmod 600 "$CRED_FILE"
unset PASSWORD

OPTS="credentials=${CRED_FILE},vers=3.1.1,uid=${UID_N},gid=${GID_N},file_mode=0755,dir_mode=0755,soft,_netdev,nofail,x-systemd.automount,x-systemd.idle-timeout=600"

BACKUP="/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
cp -a /etc/fstab "$BACKUP"
echo "Backed up /etc/fstab -> $BACKUP"

# Drop any previously managed block, then append a fresh one.
sed -i "/^${MARKER//\//\\/}$/,/^${MARKER_END//\//\\/}$/d" /etc/fstab

{
    echo "$MARKER"
    for entry in "${SHARES[@]}"; do
        share="${entry%%|*}"
        mp="${entry##*|}"
        mkdir -p "$mp"
        printf '%s %s cifs %s 0 0\n' "$share" "$mp" "$OPTS"
    done
    echo "$MARKER_END"
} >> /etc/fstab

echo "Unmounting existing manual mounts (if any)"
for entry in "${SHARES[@]}"; do
    mp="${entry##*|}"
    mountpoint -q "$mp" && umount "$mp" && echo "  umounted $mp" || true
done

systemctl daemon-reload
for entry in "${SHARES[@]}"; do
    mp="${entry##*|}"
    unit="$(systemd-escape -p --suffix=automount "$mp")"
    systemctl restart "$unit"
done

echo
echo "Verifying (first access triggers the mount)..."
for entry in "${SHARES[@]}"; do
    mp="${entry##*|}"
    if ls "$mp" >/dev/null 2>&1; then
        echo "  OK  $mp"
    else
        echo "  FAIL $mp -- check: journalctl -u $(systemd-escape -p --suffix=mount "$mp")"
    fi
done

echo "Done."
