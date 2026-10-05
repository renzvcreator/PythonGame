"""
feedback.py - Student-friendly explanations of why a shot was made or missed.

The explanation is derived from what the ball actually did (where it crossed
the height of the rim, how high it went, what it hit), so the advice always
matches the physics the player just watched.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .config import DEG
from .physics import calculate_required_velocity


@dataclass
class ShotContext:
    outcome: str                   # 'made', 'obstacle', 'rim', 'under', 'ground', 'out'
    angle: float
    velocity: float
    launch_x: float
    launch_y: float
    hoop_x: float
    hoop_y: float
    hoop_half_width: float
    cross_x: Optional[float]       # x where the ball first fell through rim height (None if never)
    max_height: float
    landing_x: float
    bounced: bool = False
    attempts: int = 1
    give_numeric_hint: bool = False
    offset_m: float = 0.0          # made shots: distance from the hoop centre


@dataclass
class Feedback:
    title: str
    headline: str
    lines: List[str] = field(default_factory=list)
    hint: str = ""


def explain_result(ctx: ShotContext) -> Feedback:
    """Build the result text shown after every shot."""
    if ctx.outcome == 'made':
        return _explain_made(ctx)
    return _explain_miss(ctx)


def _explain_made(ctx: ShotContext) -> Feedback:
    centred = abs(ctx.offset_m) <= ctx.hoop_half_width * 0.3
    title = "PERFECT SHOT!" if centred else "SHOT MADE!"
    headline = ("Your launch angle and velocity created a trajectory that passed "
                "straight through the centre of the hoop." if centred else
                "Your launch angle and velocity created a trajectory that passed through the hoop.")
    lines = []
    if ctx.bounced:
        lines.append("Bank shot! The ball bounced off the backboard and still dropped in.")
    lines.append(f"Angle {ctx.angle:.0f}{DEG} and velocity {ctx.velocity:.1f} m/s were the right combination.")
    return Feedback(title, headline, lines)


def _explain_miss(ctx: ShotContext) -> Feedback:
    fb = Feedback("MISS!", "", [])
    dx_hoop = ctx.hoop_x - ctx.launch_x

    if ctx.outcome == 'obstacle':
        fb.headline = "Your basketball hit an obstacle."
        fb.lines.append("The shape of the arc matters, not just where it lands.")
        fb.hint = ("Use a steeper angle so the ball flies higher over the obstacle, "
                   "then adjust the velocity to reach the hoop.")
        return fb

    if ctx.outcome == 'rim':
        fb.headline = "So close! The ball hit the rim."
        side = "front" if (ctx.cross_x or ctx.hoop_x) < ctx.hoop_x else "back"
        fb.lines.append(f"It came down on the {side} edge of the rim.")
        fb.hint = ("A tiny increase in velocity is all you need." if side == "front"
                   else "A tiny decrease in velocity is all you need.")
        return fb

    if ctx.outcome == 'under':
        fb.headline = "The ball came up into the hoop from below."
        fb.lines.append("A shot only counts when the ball drops through the rim from above.")
        fb.hint = "Increase the launch angle so the ball reaches the hoop while falling."
        return fb

    if ctx.bounced:
        fb.lines.append("The ball bounced off the backboard and did not drop in.")

    # Analyse the landing position relative to the hoop
    if ctx.cross_x is None:
        if ctx.max_height < ctx.hoop_y:
            fb.headline = "Too low - the ball never reached the height of the hoop."
            fb.lines.append(f"Maximum height {ctx.max_height:.1f} m, but the rim is at {ctx.hoop_y:.2f} m.")
            fb.hint = "Increase the launch angle or increase the velocity to gain height."
        else:
            fb.headline = "Too far - the ball flew past the hoop."
            fb.hint = "Reduce the velocity."
        return fb

    miss_by = ctx.cross_x - ctx.hoop_x
    if miss_by < 0:
        short = -miss_by
        fb.lines.append(f"At rim height the ball was {short:.1f} m SHORT of the hoop.")
        if ctx.angle < 35:
            fb.headline = "Too low - the arc was too flat and fell short."
            fb.hint = "Increase the launch angle for a higher arc, or increase the velocity."
        else:
            fb.headline = "Too weak - the ball did not travel far enough."
            fb.hint = "Increase the velocity."
    else:
        fb.lines.append(f"At rim height the ball was {miss_by:.1f} m PAST the hoop.")
        if ctx.angle > 55 and miss_by < dx_hoop * 0.25:
            fb.headline = "Too high - the steep arc carried the ball over the hoop."
            fb.hint = "Decrease the launch angle, or lower the velocity a little."
        else:
            fb.headline = "Too far - the ball travelled past the hoop."
            fb.hint = "Reduce the velocity."

    if ctx.give_numeric_hint and ctx.attempts >= 3:
        need = calculate_required_velocity(ctx.launch_x, ctx.launch_y, ctx.hoop_x, ctx.hoop_y, ctx.angle)
        if need is not None and 5.0 <= need <= 30.0:
            fb.lines.append(f"Physics hint: at {ctx.angle:.0f}{DEG}, about {need:.1f} m/s reaches the hoop centre.")
    return fb
