#!/usr/bin/env python3
import subprocess
import shutil
import datetime

# Define core infrastructure nodes using Tailscale IPs
NODES = {
    "Gateway (CT100)": "100.117.104.14",
    "Nepal DR Site (Pi)": "100.104.209.126"
}

MEDIA_PATH = "/mnt/media-storage"

def check_ping(ip):
    """
    Uses Proxmox 'pct exec' to ping through the CT100 Tailscale gateway.
    This allows the bare-metal host to monitor VPN nodes without installing Tailscale on the host.
    """
    try:
        # Run: pct exec 100 -- ping -c 1 -W 2 <IP>
        output = subprocess.run(
            ["pct", "exec", "100", "--", "ping", "-c", "1", "-W", "2", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return output.returncode == 0
    except Exception:
        return False

def check_storage(path):
    """Returns free space in GB."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except FileNotFoundError:
        return -1

if __name__ == "__main__":
    print(f"--- Infrastructure Health Report: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    
    print("\n[Network Status]")
    for name, ip in NODES.items():
        status = "ONLINE" if check_ping(ip) else "OFFLINE"
        print(f"{name} ({ip}): {status}")

    print("\n[Storage Status]")
    free_space = check_storage(MEDIA_PATH)
    if free_space != -1:
        print(f"Primary Media Pool: {free_space:.2f} GB free")
    else:
        print("Primary Media Pool: MOUNT POINT NOT FOUND")