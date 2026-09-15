"""Data-gathering helpers for the Pi/home status e-ink screen.

Deliberately has no PIL or EPD import (see
docs/superpowers/specs/2026-09-14-pi-status-display-design.md,
Architecture section) so this module can be imported and unit tested on
any machine, with or without e-ink hardware attached.
"""

import subprocess


def read_cpu_temp(path="/sys/class/thermal/thermal_zone0/temp"):
    try:
        with open(path) as f:
            raw = f.read().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError):
        return None


def read_uptime(path="/proc/uptime"):
    try:
        with open(path) as f:
            raw = f.read().strip()
        seconds = float(raw.split()[0])
    except (OSError, ValueError, IndexError):
        return None

    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
