# Physics Hoops: A Projectile Motion Challenge

An educational 2D basketball game written in Python (pygame). You control the
launch **angle** and **initial velocity** of a basketball; the game moves the ball
frame by frame with the real projectile-motion equations and tells you *why* every
shot went in or missed.

## Run it

```
pip install -r requirements.txt
python main.py
```

Requires Python 3.9+ and pygame 2.x. The window is 1280x720 and scales to fit the screen.

Run the physics tests with:

```
python -m unittest discover tests
```

## How to play

1. **Choose an angle** (20° to 70°) - controls how steep the arc is.
2. **Choose a velocity** (5 to 30 m/s) - controls how fast the ball leaves the launcher.
3. **Press SHOOT** - the ball flies using `x = x0 + Vx t` and `y = y0 + Vy t - ½ g t²`.
4. **Watch the trajectory** - the dotted path is the prediction; the orange dots are the real path. They coincide because both come from the same equations.
5. **Score** - the ball must fall *through* the rim from above. Touching the rim does not count.

### Controls

| Action | Mouse | Keyboard |
| --- | --- | --- |
| Angle | drag the Angle slider | Left / Right (Shift = 5° steps) |
| Velocity | drag the Velocity slider | Up / Down (Shift = 1 m/s steps) |
| Shoot | SHOOT | Space or Enter |
| Try again / Next level | TRY AGAIN / NEXT LEVEL | Space / N |
| Reset level | RESET | R |
| Pause | PAUSE | P |
| How to play | HOW TO PLAY | H |
| Velocity arrows on the ball | | V |
| Slow motion (0.25x) | | S |
| Back to level select / menu | LEVELS / MENU | Esc |
| Unlock every level (teacher mode) | | U on the level-select screen |

## Levels

| # | Level | What it teaches |
| --- | --- | --- |
| 1 | Learn the Basics | projectile motion, angle, velocity (unlimited shots, preview on) |
| 2 | Distance Challenge | range depends on angle *and* velocity |
| 3 | Height Challenge | vertical displacement, flight time, maximum height |
| 4 | Obstacle Challenge | the *shape* of the arc matters - clear the wall |
| 5 | Limited Attempts | 5 shots; plan with the information panel |
| 6 | Moving Hoop | predict where the hoop will be after the flight time |
| 7 | Advanced Mode | no preview or estimates; only angle, velocity, distance and height |
| 8 | Free Play Lab (bonus) | wind (horizontal acceleration) and air resistance toggles |

Gravity is 9.81 m/s² in every level. The trajectory is never altered to make a shot easier;
the only "forgiveness" is a wide rim and a generous ball radius.

## Scoring

| Item | Points |
| --- | --- |
| Made shot | +100 |
| Accuracy bonus (how centred the ball passed through the rim) | up to +50 |
| Efficiency bonus (1st / 2nd / 3rd / 4th attempt on a level) | +50 / +30 / +20 / +10 |
| Streak bonus (every 3 made shots in a row) | +50 |

Progress and a small leaderboard (highest score, best accuracy, fewest attempts, fastest
course completion) are stored in `physics_hoops_save.json` next to `main.py`. Delete the
file to start fresh.

## The physics, and where it lives

All equations are in [physics_hoops/physics.py](physics_hoops/physics.py) and have no
pygame dependency:

| Function | Equation |
| --- | --- |
| `calculate_velocity_components` | Vx = V0 cos θ, Vy = V0 sin θ |
| `calculate_projectile_position` | x = x0 + Vx t (+ ½ ax t²), y = y0 + Vy t − ½ g t² |
| `calculate_velocity_at_time` | vy(t) = Vy − g t |
| `calculate_flight_time` | T = (Vy + √(Vy² + 2g(y0 − y_final))) / g |
| `calculate_maximum_height` | Hmax = y0 + Vy² / 2g |
| `calculate_range` | R = Vx T |
| `calculate_times_at_height` | both moments the ball is at a given height |
| `calculate_required_velocity` / `calculate_required_angles` | solving for a target point |
| `predict_flight` | samples a whole trajectory for the dotted preview and the estimates |
| `step_projectile_numeric` | one integration step when air resistance is on (no closed form exists) |

`Projectile.update(dt)` in [entities.py](physics_hoops/entities.py) advances the ball by
accumulating time and evaluating those position equations. The information panel reads the
same numbers the ball is drawn with.

Hoop collision ([entities.py](physics_hoops/entities.py), `Hoop.check_scoring`): a shot
counts only when the ball crosses the plane of the rim while moving downward and its centre
is inside the opening. Hitting the edge is a "rim" miss, coming up from underneath is an
"under" miss. The backboard reflects the horizontal velocity (restitution 0.6) and restarts
the equations from the new state, so bank shots are possible and still pure projectile motion.

## Project structure

```
main.py                     entry point
physics_hoops/
  physics.py                projectile equations (pure functions)
  entities.py               Projectile, Hoop, Obstacle
  levels.py                 the 8 level definitions
  scoring.py                calculate_score and the bonus rules
  feedback.py               "why did I miss?" explanations
  game.py                   game states, input, shot simulation loop
  render.py                 all drawing (court, hoop, ball, preview, information panel)
  screens.py                menu, tutorial, level select, pause, course-complete screens
  demo.py                   self-playing demo shot shown in the menu and tutorial
  ui.py                     sliders, buttons, text helpers
  sounds.py                 procedurally generated sound effects
  save.py                   progress and leaderboard file
  config.py                 constants, colours, layout, world-to-screen conversion
tests/test_physics.py       unit tests (equations, collision rules, scoring, level solvability)
```

## Classroom notes

* Press **V** to show the Vx (blue), Vy (green) and resultant (red) velocity arrows on the
  ball, and **S** for slow motion. Pause with **P** mid-flight to discuss the numbers.
* The "LIVE SHOT" panel shows that Vx stays constant while Vy drops by g every second.
* After three misses on a level the result card gives a numeric hint computed from the
  required-velocity equation, so students can check their own calculation against it.
* Level 8 compares the ideal arc with wind and air resistance (numerically integrated).
