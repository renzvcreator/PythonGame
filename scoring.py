"""
scoring.py - Points for successful shots.

    Made shot            +100
    Accuracy bonus       up to +50  (how centred the ball passed through the rim)
    Efficiency bonus     +50 / +30 / +20 / +10 for 1st / 2nd / 3rd / 4th attempt
    Streak bonus         +50 every 3 made shots in a row
"""
from __future__ import annotations

from dataclasses import dataclass

BASE_POINTS = 100
MAX_ACCURACY_BONUS = 50
EFFICIENCY_TABLE = {1: 50, 2: 30, 3: 20, 4: 10}
STREAK_LENGTH = 3
STREAK_BONUS = 50


@dataclass
class ScoreBreakdown:
    base: int
    accuracy: int
    efficiency: int
    streak: int

    @property
    def total(self) -> int:
        return self.base + self.accuracy + self.efficiency + self.streak


def calculate_accuracy_bonus(offset_m: float, half_width_m: float) -> int:
    """Bonus for passing near the centre of the hoop (0 at the edge, 50 dead centre), in steps of 10."""
    if half_width_m <= 0:
        return MAX_ACCURACY_BONUS
    ratio = max(0.0, 1.0 - abs(offset_m) / half_width_m)
    return int(round(MAX_ACCURACY_BONUS * ratio / 10.0)) * 10


def calculate_efficiency_bonus(attempt_number: int) -> int:
    """Fewer attempts on a level earn a bigger bonus."""
    return EFFICIENCY_TABLE.get(attempt_number, 0)


def calculate_streak_bonus(streak: int) -> int:
    """Extra points every 3 consecutive made shots."""
    if streak > 0 and streak % STREAK_LENGTH == 0:
        return STREAK_BONUS
    return 0


def calculate_score(offset_m: float, half_width_m: float, attempt_number: int, streak: int) -> ScoreBreakdown:
    """Combine all bonuses for a made shot."""
    return ScoreBreakdown(
        base=BASE_POINTS,
        accuracy=calculate_accuracy_bonus(offset_m, half_width_m),
        efficiency=calculate_efficiency_bonus(attempt_number),
        streak=calculate_streak_bonus(streak),
    )
