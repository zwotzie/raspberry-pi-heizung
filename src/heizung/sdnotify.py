"""Minimal sd_notify implementation (no dependency); no-op outside systemd."""

import os
import socket


def notify(message: str) -> None:
    """Send a state message (e.g. "READY=1", "WATCHDOG=1") to systemd.

    Does nothing if NOTIFY_SOCKET is unset (not started by systemd).
    Send errors are ignored so a notification never crashes the daemon.

    Args:
        message: sd_notify state string, e.g. "READY=1" or "WATCHDOG=1".
    """
    path = os.environ.get("NOTIFY_SOCKET")
    if not path:
        return
    if path.startswith("@"):
        path = "\0" + path[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(path)
            sock.sendall(message.encode())
    except OSError:
        pass
