"""
Self-ping utility — keeps the Render free-tier web service alive by
hitting the /health/ endpoint every 14 minutes so the dyno never spins
down and wipes the ephemeral SQLite file.

The thread is started once from AnalyzerConfig.ready().
"""
import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

PING_INTERVAL = 14 * 60          # 14 minutes in seconds
PING_TIMEOUT  = 10                # seconds before giving up on a single ping


def _get_base_url() -> str:
    """Return the app's public base URL from the environment or fall back to localhost."""
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("ALLOWED_HOSTS", "")
    # ALLOWED_HOSTS may be a comma-separated list; take the first non-local entry
    if "," in host:
        for h in host.split(","):
            h = h.strip().lstrip(".")
            if h and h not in ("localhost", "127.0.0.1"):
                host = h
                break
    if not host or host in ("localhost", "127.0.0.1", ""):
        return None   # Don't ping in local dev
    return f"https://{host}"


def _ping_loop(base_url: str) -> None:
    """Ping /health/ forever, sleeping PING_INTERVAL between pings."""
    url = f"{base_url}/health/"
    logger.info(f"[ping] Self-ping started → {url} every {PING_INTERVAL // 60} min")
    while True:
        time.sleep(PING_INTERVAL)
        try:
            resp = requests.get(url, timeout=PING_TIMEOUT)
            logger.info(f"[ping] {url} → {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[ping] Failed to ping {url}: {exc}")


def start_ping_thread() -> None:
    """
    Start the background ping thread once.
    Safe to call from AppConfig.ready() — skips local dev automatically.
    """
    base_url = _get_base_url()
    if not base_url:
        logger.info("[ping] Local environment detected — self-ping disabled.")
        return

    t = threading.Thread(target=_ping_loop, args=(base_url,), daemon=True, name="self-ping")
    t.start()
