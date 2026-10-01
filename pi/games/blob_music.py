"""Procedural BlobJump BGM — calm/intense loops crossfade with run speed."""

from __future__ import annotations

import array
import math
import os
from typing import Optional

import pygame

SAMPLE_RATE = 22050
_MUSIC_ENABLED = os.environ.get("BODY_MUSIC", "1") not in ("0", "false", "False")


def _clamp_sample(x: float) -> int:
    return int(max(-32767, min(32767, x * 32767)))


def _ensure_mixer() -> bool:
    if not _MUSIC_ENABLED:
        return False
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(SAMPLE_RATE, size=-16, channels=2, buffer=512)
        except pygame.error:
            return False
    return True


def _render_loop(bpm: float, energy: float) -> Optional[pygame.mixer.Sound]:
    """energy 0 = calmer mix, 1 = harder obstacles / top speed."""
    sr = SAMPLE_RATE
    beats = 8
    beat_len = sr * 60.0 / bpm
    n = int(beats * beat_len)
    if n < 1:
        return None

    # Pentatonic arpeggio (Hz)
    arp = [523.25, 587.33, 659.25, 783.99, 880.0, 783.99, 659.25, 587.33]
    bass = [130.81, 146.83, 164.81, 146.83, 130.81, 123.47, 130.81, 146.83]

    mono = [0.0] * n
    eighth = beat_len / 2.0
    steps = int(beats * 2)

    for step in range(steps):
        s0 = int(step * eighth)
        s1 = int((step + 1) * eighth)
        f = arp[step % len(arp)]
        mel_vol = 0.035 + 0.055 * energy
        for i in range(s0, min(s1, n)):
            t = (i - s0) / max(1, eighth)
            env = math.exp(-4.0 * t) if energy < 0.7 else math.exp(-2.5 * t)
            mono[i] += mel_vol * env * math.sin(2 * math.pi * f * i / sr)

        if step % 2 == 0:
            beat = step // 2
            b0 = int(beat * beat_len)
            b1 = int((beat + 1) * beat_len)
            bf = bass[beat % len(bass)]
            bvol = 0.06 + 0.14 * energy
            for i in range(b0, min(b1, n)):
                t = (i - b0) / max(1, beat_len)
                mono[i] += bvol * (1.0 - t * 0.35) * math.sin(2 * math.pi * bf * i / sr)
                if i - b0 < beat_len * 0.04:
                    kick = (0.12 + 0.12 * energy) * (1.0 - (i - b0) / (beat_len * 0.04))
                    mono[i] += kick * math.sin(2 * math.pi * 55 * (i - b0) / sr)

        if energy > 0.35 and step % 2 == 1:
            h0 = int(step * eighth)
            h1 = min(n, h0 + int(sr * 0.012))
            hat_vol = 0.025 * (energy - 0.35) / 0.65
            for i in range(h0, h1):
                # cheap noise burst
                mono[i] += hat_vol * math.sin(i * 12.9898) * math.cos(i * 78.233)

    stereo = array.array("h")
    for s in mono:
        v = _clamp_sample(s)
        stereo.append(v)
        stereo.append(v)

    try:
        return pygame.mixer.Sound(buffer=stereo.tobytes())
    except pygame.error:
        return None


class BlobJumpMusic:
    """Two looping layers; volumes follow game intensity (0..1)."""

    def __init__(self) -> None:
        self._ready = _ensure_mixer()
        self._calm: Optional[pygame.mixer.Sound] = None
        self._intense: Optional[pygame.mixer.Sound] = None
        self._ch_calm: Optional[pygame.mixer.Channel] = None
        self._ch_intense: Optional[pygame.mixer.Channel] = None
        self._level = 0.0
        self._playing = False
        if self._ready:
            self._calm = _render_loop(108, 0.0)
            self._intense = _render_loop(128, 1.0)

    def start(self) -> None:
        if not self._ready or not self._calm or not self._intense:
            return
        self._ch_calm = self._calm.play(loops=-1)
        self._ch_intense = self._intense.play(loops=-1)
        if self._ch_calm:
            self._ch_calm.set_volume(0.55)
        if self._ch_intense:
            self._ch_intense.set_volume(0.0)
        self._playing = True

    def stop(self) -> None:
        if self._ch_calm:
            self._ch_calm.stop()
        if self._ch_intense:
            self._ch_intense.stop()
        self._playing = False

    def update(self, intensity: float, dt: float) -> None:
        if not self._playing or not self._ch_calm or not self._ch_intense:
            return
        target = max(0.0, min(1.0, intensity))
        # smooth crossfade
        blend = 5.0
        self._level += (target - self._level) * min(1.0, dt * blend)
        master = 0.42
        self._ch_calm.set_volume(master * (1.0 - self._level))
        self._ch_intense.set_volume(master * self._level)
