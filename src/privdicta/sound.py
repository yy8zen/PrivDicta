"""録音の開始・終了の効果音（要件 R4.5）。音はその場で合成し、ファイルを同梱しない。"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger(__name__)

RATE = 44100


def _tone(freqs: list[float], length: float = 0.07, volume: float = 0.18) -> np.ndarray:
    parts = []
    for f in freqs:
        t = np.arange(int(RATE * length)) / RATE
        wave = np.sin(2 * np.pi * f * t)
        # 立ち上がりと終わりを滑らかにして、プツッという音を防ぐ
        fade = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.01)
        parts.append(wave * fade * volume)
    return np.concatenate(parts).astype(np.float32)


START = _tone([660, 990])  # 上がる音
STOP = _tone([990, 660])  # 下がる音
ERROR = _tone([300, 300])


def play(kind: str) -> None:
    try:
        import sounddevice as sd

        sd.play({"start": START, "stop": STOP, "error": ERROR}[kind], RATE, blocking=False)
    except Exception:  # 出力デバイスがないなど。音が鳴らなくても動作は続ける
        log.debug("効果音を鳴らせませんでした", exc_info=True)
