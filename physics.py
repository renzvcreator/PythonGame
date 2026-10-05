"""
physics.py - Pure projectile-motion mathematics for Physics Hoops.

Everything in this module is plain Python (no pygame), so the SAME equations
drive the ball's movement, the trajectory preview, the information panel and
the unit tests.  Nothing in the game animates the ball along a pre-drawn
curve; every frame the ball position is computed from these functions.

Equations (SI units: metres, seconds, m/s, m/s^2):

    Vx    = V0 * cos(theta)                horizontal velocity component
    Vy    = V0 * sin(theta)                vertical velocity component
    x(t)  = x0 + Vx*t  (+ 1/2 * ax * t^2)  horizontal position (ax = wind)
    y(t)  = y0 + Vy*t  -  1/2 * g  * t^2   vertical position
    vy(t) = Vy - g*t                       vertical velocity over time
    T     = (Vy + sqrt(Vy^2 + 2 g (y0 - y_final))) / g   time of flight
    Hmax  = y0 + Vy^2 / (2 g)              maximum height
    R     = Vx * T                         horizontal range
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Acceleration due to gravity (m/s^2). Never changed by the standard levels.
G = 9.81

# Quadratic drag coefficient per unit mass for a basketball (1/m):
#   k = 0.5 * rho_air * Cd * A / m   with rho=1.225, Cd=0.47, A=0.0452 m^2, m=0.62 kg
BASKETBALL_DRAG_K = 0.021


@dataclass
class Environment:
    """Physical environment a shot is fired in."""
    g: float = G             # gravity (m/s^2)
    wind_ax: float = 0.0     # horizontal acceleration caused by wind (m/s^2), + = to the right
    drag_k: float = 0.0      # air-resistance coefficient (0 = ideal projectile motion)

    @property
    def is_ideal(self) -> bool:
        """True when the closed-form projectile equations describe the motion exactly."""
        return self.drag_k <= 0.0


# --------------------------------------------------------------------------- #
# Core equations                                                               #
# --------------------------------------------------------------------------- #
def calculate_velocity_components(v0: float, angle_deg: float) -> Tuple[float, float]:
    """Split the launch speed into (Vx, Vy): Vx = V0 cos(theta), Vy = V0 sin(theta)."""
    theta = math.radians(angle_deg)
    return v0 * math.cos(theta), v0 * math.sin(theta)


def calculate_projectile_position(x0: float, y0: float, vx: float, vy: float, t: float,
                                  g: float = G, ax: float = 0.0) -> Tuple[float, float]:
    """Position after time t:  x = x0 + Vx t + 1/2 ax t^2,   y = y0 + Vy t - 1/2 g t^2."""
    x = x0 + vx * t + 0.5 * ax * t * t
    y = y0 + vy * t - 0.5 * g * t * t
    return x, y


def calculate_velocity_at_time(vx: float, vy: float, t: float,
                               g: float = G, ax: float = 0.0) -> Tuple[float, float]:
    """Velocity after time t. Horizontal speed only changes with wind; vertical speed loses g every second."""
    return vx + ax * t, vy - g * t


def calculate_time_to_peak(vy: float, g: float = G) -> float:
    """Time until the vertical velocity becomes zero (top of the arc)."""
    return max(0.0, vy / g)


def calculate_maximum_height(y0: float, vy: float, g: float = G) -> float:
    """Highest point reached: Hmax = y0 + Vy^2 / (2g). If fired downward, the start is the highest point."""
    if vy <= 0:
        return y0
    return y0 + (vy * vy) / (2.0 * g)


def calculate_flight_time(y0: float, vy: float, g: float = G, y_final: float = 0.0) -> Optional[float]:
    """
    Time until the projectile descends to height y_final.
    Solves  y0 + Vy t - 1/2 g t^2 = y_final  for the larger (descending) root.
    Returns None if that height is never reached.
    """
    disc = vy * vy + 2.0 * g * (y0 - y_final)
    if disc < 0:
        return None
    return (vy + math.sqrt(disc)) / g


def calculate_range(vx: float, flight_time: float, ax: float = 0.0) -> float:
    """Horizontal distance covered during the flight: R = Vx T (+ 1/2 ax T^2 with wind)."""
    return vx * flight_time + 0.5 * ax * flight_time * flight_time


def calculate_times_at_height(y0: float, vy: float, y_target: float,
                              g: float = G) -> Optional[Tuple[float, float]]:
    """
    The two moments the ball is at height y_target: (t_rising, t_falling).
    Returns None if the ball never gets that high.
    """
    disc = vy * vy - 2.0 * g * (y_target - y0)
    if disc < 0:
        return None
    root = math.sqrt(disc)
    return (vy - root) / g, (vy + root) / g


def calculate_required_velocity(x0: float, y0: float, tx: float, ty: float,
                                angle_deg: float, g: float = G) -> Optional[float]:
    """
    Launch speed needed to pass through (tx, ty) at a given angle.
        V0^2 = g dx^2 / (2 cos^2(theta) (dx tan(theta) - dy))
    Returns None if the target cannot be reached at that angle.
    """
    dx, dy = tx - x0, ty - y0
    if dx <= 0:
        return None
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    denom = 2.0 * c * c * (dx * math.tan(theta) - dy)
    if denom <= 1e-9:
        return None
    return math.sqrt(g * dx * dx / denom)


def calculate_required_angles(x0: float, y0: float, tx: float, ty: float,
                              v0: float, g: float = G) -> List[float]:
    """
    Launch angles (degrees) that pass through (tx, ty) at speed v0.
        tan(theta) = (V0^2 +/- sqrt(V0^4 - g (g dx^2 + 2 dy V0^2))) / (g dx)
    Returns 0, 1 or 2 angles (low arc first).
    """
    dx, dy = tx - x0, ty - y0
    if dx <= 0:
        return []
    v2 = v0 * v0
    disc = v2 * v2 - g * (g * dx * dx + 2.0 * dy * v2)
    if disc < 0:
        return []
    root = math.sqrt(disc)
    low = math.degrees(math.atan((v2 - root) / (g * dx)))
    high = math.degrees(math.atan((v2 + root) / (g * dx)))
    return sorted({round(low, 6), round(high, 6)})


# --------------------------------------------------------------------------- #
# Numerical integration (only used when air resistance is switched on)        #
# --------------------------------------------------------------------------- #
def step_projectile_numeric(x: float, y: float, vx: float, vy: float, dt: float,
                            env: Environment) -> Tuple[float, float, float, float]:
    """
    One semi-implicit Euler step with gravity, wind and quadratic air drag:
        a = (wind, -g) - k |v| v
    """
    speed = math.hypot(vx, vy)
    ax = env.wind_ax - env.drag_k * speed * vx
    ay = -env.g - env.drag_k * speed * vy
    vx += ax * dt
    vy += ay * dt
    x += vx * dt
    y += vy * dt
    return x, y, vx, vy


# --------------------------------------------------------------------------- #
# Whole-flight prediction (trajectory preview + information panel)            #
# --------------------------------------------------------------------------- #
@dataclass
class FlightPrediction:
    points: List[Tuple[float, float, float]] = field(default_factory=list)  # (t, x, y)
    flight_time: float = 0.0     # seconds until the ball reaches y_floor
    max_height: float = 0.0      # metres above the ground
    range: float = 0.0           # horizontal distance from launch to landing
    landing_x: float = 0.0
    apex: Tuple[float, float] = (0.0, 0.0)
    uses_drag: bool = False


def predict_flight(x0: float, y0: float, v0: float, angle_deg: float,
                   env: Optional[Environment] = None, y_floor: float = 0.0,
                   dt: float = 0.02, x_limit: Optional[float] = None,
                   max_time: float = 30.0) -> FlightPrediction:
    """
    Sample the full trajectory of a shot.  With no air resistance the samples come
    straight from the closed-form equations; with air resistance they come from
    numerical integration of the same forces.
    """
    env = env or Environment()
    vx, vy = calculate_velocity_components(v0, angle_deg)
    pred = FlightPrediction(uses_drag=not env.is_ideal)
    pred.points.append((0.0, x0, y0))

    if env.is_ideal:
        total = calculate_flight_time(y0, vy, env.g, y_floor)
        if total is None:
            total = max_time
        pred.flight_time = total
        pred.max_height = calculate_maximum_height(y0, vy, env.g)
        t_peak = calculate_time_to_peak(vy, env.g)
        pred.apex = calculate_projectile_position(x0, y0, vx, vy, t_peak, env.g, env.wind_ax)
        t = dt
        while t < total:
            x, y = calculate_projectile_position(x0, y0, vx, vy, t, env.g, env.wind_ax)
            pred.points.append((t, x, y))
            if x_limit is not None and x > x_limit:
                break
            t += dt
        land_x, land_y = calculate_projectile_position(x0, y0, vx, vy, total, env.g, env.wind_ax)
        pred.points.append((total, land_x, land_y))
        pred.landing_x = land_x
        pred.range = land_x - x0
        return pred

    # Numerical path with air resistance
    x, y, cvx, cvy = x0, y0, vx, vy
    t = 0.0
    sub = 5
    h = dt / sub
    pred.max_height = y0
    pred.apex = (x0, y0)
    while t < max_time:
        px, py = x, y
        for _ in range(sub):
            x, y, cvx, cvy = step_projectile_numeric(x, y, cvx, cvy, h, env)
        t += dt
        if y > pred.max_height:
            pred.max_height = y
            pred.apex = (x, y)
        if y <= y_floor and t > dt:
            # interpolate the exact landing point
            frac = (py - y_floor) / (py - y) if py != y else 1.0
            lx = px + (x - px) * frac
            pred.points.append((t, lx, y_floor))
            pred.flight_time = t - dt + dt * frac
            pred.landing_x = lx
            pred.range = lx - x0
            return pred
        pred.points.append((t, x, y))
        if x_limit is not None and x > x_limit:
            break
    pred.flight_time = t
    pred.landing_x = x
    pred.range = x - x0
    return pred
