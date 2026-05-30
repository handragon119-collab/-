# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
wake_listener.py — optional double-clap wake detector.

Runs as a small standalone process. It listens to the microphone with
sounddevice, detects two sharp transients (claps) close together, and POSTs to
JARVIS's /api/wake endpoint so the orb can wake up hands-free.

Enable via .env:
    JARVIS_WAKE_KEY=...        (must match the server's key)
    JARVIS_WAKE_URL=https://localhost:8340/api/wake
    JARVIS_CLAP_THRESHOLD=0.30

Run:  python helpers/wake_listener.py
"""

from __future__ import annotations

import os
import time

import httpx

try:
    import numpy as np
    import sounddevice as sd
    _HAVE_AUDIO = True
except Exception:  # pragma: no cover
    _HAVE_AUDIO = False

WAKE_URL = os.environ.get("JARVIS_WAKE_URL", "https://localhost:8340/api/wake")
WAKE_KEY = os.environ.get("JARVIS_WAKE_KEY", "")
THRESHOLD = float(os.environ.get("JARVIS_CLAP_THRESHOLD", "0.30"))
SAMPLE_RATE = 44100
BLOCK = 1024
DOUBLE_CLAP_WINDOW = 0.6  # seconds between the two claps
COOLDOWN = 2.0            # seconds before we can wake again


def _fire_wake() -> None:
    try:
        httpx.post(WAKE_URL, json={"key": WAKE_KEY}, verify=False, timeout=5.0)
        print("👏👏  Wake sent.")
    except Exception as exc:
        print(f"wake POST failed: {exc}")


def main() -> None:
    if not _HAVE_AUDIO:
        raise SystemExit("sounddevice/numpy not installed — run: pip install -r requirements.txt")

    print(f"Wake listener armed (threshold={THRESHOLD}). Double-clap to wake JARVIS.")
    last_clap = 0.0
    last_wake = 0.0

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        nonlocal last_clap, last_wake
        if status:
            return
        peak = float(np.max(np.abs(indata)))
        now = time.time()
        if peak > THRESHOLD and (now - last_wake) > COOLDOWN:
            if (now - last_clap) < DOUBLE_CLAP_WINDOW:
                _fire_wake()
                last_wake = now
                last_clap = 0.0
            else:
                last_clap = now

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                        blocksize=BLOCK, callback=callback):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nWake listener stopped.")


if __name__ == "__main__":
    main()
