#!/usr/bin/env python3
import subprocess
import shutil
import datetime
import sys

# Define core infrastructure nodes using Tailscale IPs
NODES = {
    "Gateway (CT100)": "100.117.104.14",
    "Nepal DR Site (Pi)": "100.104.209.126"
}

MEDIA_PATH = "/mnt/media-storage"
LOG_FILE = "/var/log/healthcheck.log"


def log(message):
    """Prints to stdout and appends to the log file."""
    print(message)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(message + "\n")
    except OSError as e:
        print(f"WARNING: Could not write to {LOG_FILE}: {e}", file=sys.stderr)


def check_ping(ip):
    """
    Uses Proxmox 'pct exec' to ping through the CT100 Tailscale gateway.
    This allows the bare-metal host to monitor VPN nodes without installing Tailscale on the host.
    """
    try:
        # Run: pct exec 100 -- ping -c 1 -W 2 <IP>
        result = subprocess.run(
            ["pct", "exec", "100", "--", "ping", "-c", "1", "-W", "2", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except FileNotFoundError:
        log(f"ERROR: 'pct' command not found. Is this running on the Proxmox host?")
        return False
    except OSError as e:
        log(f"ERROR: Failed to execute ping for {ip}: {e}")
        return False


def check_storage(path):
    """Returns free space in GB, or -1 if the path does not exist."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except FileNotFoundError:
        return -1


if __name__ == "__main__":
    has_failures = False

    log(f"--- Infrastructure Health Report: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} ---")

    log("\n[Network Status]")
    for name, ip in NODES.items():
        is_online = check_ping(ip)
        status = "ONLINE" if is_online else "OFFLINE"
        log(f"{name} ({ip}): {status}")
        if not is_online:
            has_failures = True

    log("\n[Storage Status]")
    free_space = check_storage(MEDIA_PATH)
    if free_space != -1:
        log(f"Primary Media Pool: {free_space:.2f} GB free")
    else:
        log("Primary Media Pool: MOUNT POINT NOT FOUND")
        has_failures = True

    sys.exit(1 if has_failures else 0)