"""
levels.py - Progressive level definitions.

Every level uses the same gravity (9.81 m/s^2).  Levels differ only in where
the hoop is, what is in the way, how many shots you get and how much help the
trajectory preview gives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import DEFAULT_LAUNCH


@dataclass
class Level:
    number: int
    name: str
    subtitle: str
    teaches: List[str]
    hoop_x: float
    hoop_y: float
    launch: Tuple[float, float] = DEFAULT_LAUNCH
    obstacles: List[Tuple[float, float, float, float]] = field(default_factory=list)  # (x, y_bottom, w, h)
    max_shots: Optional[int] = None          # None = unlimited attempts
    hoop_move_amplitude: float = 0.0         # metres
    hoop_move_period: float = 0.0            # seconds
    show_preview: bool = True                # dotted trajectory preview
    show_estimates: bool = True              # flight time / max height / range in the panel
    allow_env_controls: bool = False         # wind and air-resistance toggles (Free Play)
    tip: str = ""
    bonus: bool = False                      # not part of the main course


LEVELS: List[Level] = [
    Level(
        number=1, name="LEARN THE BASICS",
        subtitle="Experiment freely. Unlimited shots.",
        teaches=["Projectile motion", "Angle", "Velocity"],
        hoop_x=10.0, hoop_y=3.05,
        tip="Move the sliders and watch the dotted path change. A steeper angle makes a taller arc; "
            "more velocity sends the ball farther.",
    ),
    Level(
        number=2, name="DISTANCE CHALLENGE",
        subtitle="The hoop is far away.",
        teaches=["Range", "Initial velocity", "Angle"],
        hoop_x=22.0, hoop_y=3.05,
        tip="Range depends on BOTH angle and velocity. For a given speed, about 45 degrees gives the "
            "longest flat-ground range.",
    ),
    Level(
        number=3, name="HEIGHT CHALLENGE",
        subtitle="The hoop is high above you.",
        teaches=["Vertical displacement", "Gravity", "Flight time", "Launch height"],
        hoop_x=15.0, hoop_y=7.0,
        tip="The ball must still be ABOVE the rim when it arrives and be falling. "
            "Check the estimated maximum height.",
    ),
    Level(
        number=4, name="OBSTACLE CHALLENGE",
        subtitle="Arc the ball over the wall.",
        teaches=["Trajectory shape", "Maximum height"],
        hoop_x=20.0, hoop_y=3.05,
        obstacles=[(10.0, 0.0, 1.0, 6.0)],
        tip="A flat shot hits the wall. Use a steeper angle so the arc clears it, then tune the velocity.",
    ),
    Level(
        number=5, name="LIMITED ATTEMPTS",
        subtitle="Only 5 shots. Think before you shoot!",
        teaches=["Prediction", "Efficiency"],
        hoop_x=18.0, hoop_y=4.5, max_shots=5,
        tip="Read the information panel before shooting. Fewer attempts earn a bigger efficiency bonus.",
    ),
    Level(
        number=6, name="MOVING HOOP",
        subtitle="The hoop slides side to side.",
        teaches=["Flight time", "Prediction"],
        hoop_x=18.0, hoop_y=3.05,
        hoop_move_amplitude=2.5, hoop_move_period=8.0,
        tip="Where will the hoop be after the flight time? Shoot when the hoop is moving TOWARD "
            "the spot where your ball will come down.",
    ),
    Level(
        number=7, name="ADVANCED MODE",
        subtitle="No trajectory preview. Apply what you learned.",
        teaches=["Everything so far"],
        hoop_x=24.0, hoop_y=5.5,
        obstacles=[(14.0, 0.0, 1.0, 6.0)],
        max_shots=8, show_preview=False, show_estimates=False,
        tip="You only get the angle, velocity, distance and height. Picture the arc in your mind "
            "and use what you learned about range and maximum height.",
    ),
    Level(
        number=8, name="FREE PLAY LAB",
        subtitle="Bonus: experiment with wind and air resistance.",
        teaches=["Wind", "Air resistance"],
        hoop_x=14.0, hoop_y=3.05, allow_env_controls=True, bonus=True,
        tip="Turn on wind or air resistance and compare the dotted prediction with the ideal arc.",
    ),
]

MAIN_COURSE_COUNT = sum(1 for lv in LEVELS if not lv.bonus)


def get_level(index: int) -> Level:
    return LEVELS[index]
