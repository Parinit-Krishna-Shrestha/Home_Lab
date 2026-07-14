#!/bin/bash
# ==============================================================================
# Script: dr_sync.sh
# Purpose: Automated disaster recovery push across Tailscale Mesh
# ==============================================================================

DEST_USER="pi"
DEST_HOST="100.104.209.126" # Raspberry Pi Tailscale IP
SOURCE_DIR="/mnt/media-storage/"
DEST_DIR="/mnt/backup/japan_nas_sync/"
LOG_FILE="/var/log/dr_sync.log"

echo "--- Starting DR Sync: $(date) ---" | tee -a "$LOG_FILE"

# Ensure destination directory exists on the persistent mount in Nepal
ssh -o StrictHostKeyChecking=accept-new "${DEST_USER}@${DEST_HOST}" "mkdir -p ${DEST_DIR}"

# Execute rsync over SSH (Tailscale encrypted tunnel)
# --exclude: Ignores system files that cause permission errors
# --bwlimit=2000: Limits speed to 2000 KB/s (~16 Mbps) to prevent network lag (remove or adjust as needed)
rsync -avh --delete \
  --exclude 'lost+found' \
  --exclude '.Trash-*' \
  --bwlimit=2000 \
  -e "ssh -o StrictHostKeyChecking=accept-new" \
  "${SOURCE_DIR}" \
  "${DEST_USER}@${DEST_HOST}:${DEST_DIR}" 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "--- Sync Completed Successfully: $(date) ---" | tee -a "$LOG_FILE"
else
    echo "--- Sync FAILED: $(date) ---" | tee -a "$LOG_FILE"
fi