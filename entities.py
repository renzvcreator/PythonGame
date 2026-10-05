"""
entities.py - Game objects: the basketball (projectile), hoop and obstacles.

The Projectile class is the bridge between the physics module and the game:
its update() method advances the shot by a time step using the projectile
equations and nothing else.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .config import BALL_RADIUS_M, HOOP_WIDTH_M
from .physics import (Environment, calculate_projectile_position, calculate_velocity_at_time,
                      calculate_velocity_components, step_projectile_numeric)


class Projectile:
    """The basketball in flight.  All movement comes from physics.py."""

    def __init__(self, x0: float, y0: float, v0: float, angle_deg: float,
                 env: Optional[Environment] = None, radius: float = BALL_RADIUS_M):
        self.env = env or Environment()
        self.radius = radius
        self.launch_x, self.launch_y = x0, y0
        self.v0 = v0
        self.angle = angle_deg
        # Reference state for the analytic equations (changes after a bounce)
        self.x0, self.y0 = x0, y0
        self.vx0, self.vy0 = calculate_velocity_components(v0, angle_deg)
        self.t = 0.0            # time since the current reference state
        self.elapsed = 0.0      # total time of flight
        self.x, self.y = x0, y0
        self.prev_x, self.prev_y = x0, y0
        self.vx, self.vy = self.vx0, self.vy0
        self.max_height = y0
        self.bounces = 0
        self.spin = 0.0          # visual rotation (radians)
        self.trail: List[Tuple[float, float]] = [(x0, y0)]

    def update(self, dt: float) -> None:
        """Advance the ball by dt seconds using the projectile-motion equations."""
        self.prev_x, self.prev_y = self.x, self.y
        if self.env.is_ideal:
            # Closed-form motion: x(t) = x0 + Vx t,  y(t) = y0 + Vy t - 1/2 g t^2
            self.t += dt
            self.x, self.y = calculate_projectile_position(
                self.x0, self.y0, self.vx0, self.vy0, self.t, self.env.g, self.env.wind_ax)
            self.vx, self.vy = calculate_velocity_at_time(
                self.vx0, self.vy0, self.t, self.env.g, self.env.wind_ax)
        else:
            # Air resistance has no closed form: integrate the same forces numerically.
            sub = 4
            h = dt / sub
            for _ in range(sub):
                self.x, self.y, self.vx, self.vy = step_projectile_numeric(
                    self.x, self.y, self.vx, self.vy, h, self.env)
            self.t += dt
        self.elapsed += dt
        self.max_height = max(self.max_height, self.y)
        self.spin += (self.x - self.prev_x) / self.radius
        lx, ly = self.trail[-1]
        if (self.x - lx) ** 2 + (self.y - ly) ** 2 >= 0.25 ** 2:
            self.trail.append((self.x, self.y))

    def rebase(self, x: float, y: float, vx: float, vy: float) -> None:
        """Restart the equations from a new state (after a backboard bounce)."""
        self.x0, self.y0 = x, y
        self.vx0, self.vy0 = vx, vy
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.t = 0.0
        self.bounces += 1

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def position(self) -> Tuple[float, float]:
        return self.x, self.y


class Hoop:
    """A basketball hoop: rim, net and backboard.  Can oscillate horizontally."""

    NET_DEPTH = 0.9
    BACKBOARD_GAP = 0.25
    BACKBOARD_THICKNESS = 0.15
    BACKBOARD_BELOW = 0.4
    BACKBOARD_ABOVE = 1.8

    def __init__(self, x: float, y: float, width: float = HOOP_WIDTH_M,
                 move_amplitude: float = 0.0, move_period: float = 0.0):
        self.base_x = x
        self.x = x
        self.y = y
        self.width = width
        self.move_amplitude = move_amplitude
        self.move_period = move_period

    @property
    def moving(self) -> bool:
        return self.move_amplitude > 0 and self.move_period > 0

    def update(self, time: float) -> None:
        """Moving hoops follow x = base + A sin(2 pi t / P)."""
        if self.moving:
            self.x = self.base_x + self.move_amplitude * math.sin(2 * math.pi * time / self.move_period)

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2

    def backboard_rect(self) -> Tuple[float, float, float, float]:
        """(x, y_bottom, w, h) of the backboard in world metres."""
        return (self.right + self.BACKBOARD_GAP, self.y - self.BACKBOARD_BELOW,
                self.BACKBOARD_THICKNESS, self.BACKBOARD_BELOW + self.BACKBOARD_ABOVE)

    def check_scoring(self, prev_x: float, prev_y: float, x: float, y: float,
                      radius: float) -> Tuple[Optional[str], Optional[float]]:
        """
        Evaluate the ball as it crosses the plane of the rim.

        Returns (result, x_at_crossing) where result is:
          'made'   - ball dropped through the opening from above
          'rim'    - ball hit the rim while dropping
          'passed' - ball crossed rim height while falling but away from the hoop
          'under'  - ball came up through/into the rim from below
          None     - the rim plane was not crossed this step
        """
        if prev_y > self.y >= y:                      # moving downward across rim height
            frac = (prev_y - self.y) / (prev_y - y) if prev_y != y else 1.0
            xc = prev_x + (x - prev_x) * frac
            margin = radius * 0.5                     # forgiving: half the ball may overlap the rim
            if self.left + margin <= xc <= self.right - margin:
                return 'made', xc
            if self.left - radius <= xc <= self.right + radius:
                return 'rim', xc
            return 'passed', xc
        if prev_y < self.y <= y:                      # moving upward across rim height
            frac = (self.y - prev_y) / (y - prev_y) if prev_y != y else 1.0
            xc = prev_x + (x - prev_x) * frac
            if self.left - radius <= xc <= self.right + radius:
                return 'under', xc
        return None, None

    def hits_backboard(self, ball: Projectile) -> bool:
        """True when the ball, moving right, overlaps the front face of the backboard."""
        bx, by, bw, bh = self.backboard_rect()
        if ball.vx <= 0 or ball.x > bx:
            return False
        return (ball.x + ball.radius >= bx and by <= ball.y <= by + bh)


class Obstacle:
    """An axis-aligned block the ball must not touch."""

    def __init__(self, x: float, y: float, w: float, h: float, label: str = ""):
        self.x, self.y, self.w, self.h = x, y, w, h    # y is the bottom edge
        self.label = label

    @property
    def top(self) -> float:
        return self.y + self.h

    @property
    def right(self) -> float:
        return self.x + self.w

    def collides_circle(self, cx: float, cy: float, r: float) -> bool:
        nx = min(max(cx, self.x), self.right)
        ny = min(max(cy, self.y), self.top)
        return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r
