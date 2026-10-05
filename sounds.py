"""
sounds.py - Tiny procedurally generated sound effects (no external files).

If the audio device is unavailable the game runs silently.
"""
from __future__ import annotations

import math
import random
from array import array

import pygame

SAMPLE_RATE = 22050


def _samples(duration: float):
    return int(SAMPLE_RATE * duration)


def _make_sound(buf: array):
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _tone(freq: float, duration: float, volume: float = 0.4, decay: bool = True, freq_end=None) -> array:
    n = _samples(duration)
    buf = array('h')
    f_end = freq_end if freq_end is not None else freq
    phase = 0.0
    for i in range(n):
        frac = i / n
        f = freq + (f_end - freq) * frac
        phase += 2 * math.pi * f / SAMPLE_RATE
        env = (1.0 - frac) if decay else 1.0
        buf.append(int(32767 * volume * env * math.sin(phase)))
    return buf


def _noise(duration: float, volume: float = 0.3) -> array:
    n = _samples(duration)
    buf = array('h')
    rnd = random.Random(7)
    last = 0.0
    for i in range(n):
        frac = i / n
        # low-pass filtered noise for a soft "swish"
        last = 0.85 * last + 0.15 * rnd.uniform(-1, 1)
        env = math.sin(math.pi * frac)
        buf.append(int(32767 * volume * env * last * 3))
    return buf


def _concat(*parts: array) -> array:
    out = array('h')
    for p in parts:
        out.extend(p)
    return out


class SoundBank:
    """Plays named effects: 'shoot', 'swish', 'score', 'miss', 'bounce', 'click', 'rim'."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            self.sounds = {
                'shoot': _make_sound(_tone(220, 0.12, 0.35, True, 120)),
                'swish': _make_sound(_noise(0.35, 0.35)),
                'score': _make_sound(_concat(_tone(523, 0.12, 0.35), _tone(659, 0.12, 0.35), _tone(784, 0.25, 0.4))),
                'miss': _make_sound(_tone(300, 0.4, 0.35, True, 120)),
                'bounce': _make_sound(_tone(160, 0.15, 0.5, True, 90)),
                'rim': _make_sound(_tone(900, 0.2, 0.3, True, 600)),
                'click': _make_sound(_tone(1200, 0.03, 0.2)),
                'tick': _make_sound(_tone(800, 0.015, 0.08)),
            }
            self.enabled = True
        except Exception:
            self.enabled = False

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
