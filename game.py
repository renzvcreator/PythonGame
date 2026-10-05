"""
game.py - Game states, input handling and the shot simulation loop.

State flow:
    MENU -> TUTORIAL -> LEVEL_SELECT -> AIMING -> SHOOTING -> RESULT -> (AIMING | next level)
    PAUSED and HOW_TO_PLAY can be entered from the play states and return to them.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

import pygame

from . import config as C
from .demo import DemoShot
from .entities import Hoop, Obstacle, Projectile
from .feedback import Feedback, ShotContext, explain_result
from .levels import LEVELS, MAIN_COURSE_COUNT, Level
from .physics import BASKETBALL_DRAG_K, Environment, predict_flight
from .render import Renderer
from .save import SaveData
from .scoring import ScoreBreakdown, calculate_score
from .sounds import SoundBank
from .ui import Button, Slider
from . import screens


class State(Enum):
    MENU = auto()
    TUTORIAL = auto()
    LEVEL_SELECT = auto()
    AIMING = auto()
    SHOOTING = auto()
    RESULT = auto()
    PAUSED = auto()
    HOW_TO_PLAY = auto()
    GAME_COMPLETE = auto()


PLAY_STATES = (State.AIMING, State.SHOOTING, State.RESULT, State.PAUSED)


@dataclass
class ShotResult:
    outcome: str
    made: bool
    feedback: Feedback
    breakdown: Optional[ScoreBreakdown]
    angle: float
    velocity: float
    flight_time: float
    max_height: float
    distance: float
    level_failed: bool = False


class Game:
    def __init__(self):
        pygame.init()
        self.sounds = SoundBank()
        self.screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer()
        self.fonts = self.renderer.fonts
        self.save = SaveData.load()
        self.demo = DemoShot(pygame.Rect(0, 0, 10, 10))

        self.state = State.MENU
        self.return_state = State.MENU
        self.running = True

        # Level / world
        self.level_index = 0
        self.level: Optional[Level] = None
        self.hoop: Optional[Hoop] = None
        self.obstacles: List[Obstacle] = []
        self.ball: Optional[Projectile] = None
        self.env = Environment()
        self.level_time = 0.0
        self.time_scale = 1.0
        self.show_vectors = True
        self.physics_acc = 0.0

        # Aim
        self.angle = float(C.DEFAULT_ANGLE)
        self.velocity = float(C.DEFAULT_VELOCITY)
        self.preview = None

        # Progress
        self.total_score = 0
        self.streak = 0
        self.attempts = 0
        self.shots_left: Optional[int] = None
        self.level_score = 0
        self.result: Optional[ShotResult] = None
        self.cross_x: Optional[float] = None
        self.session_start: Optional[float] = None
        self.course_time: Optional[float] = None
        self.shots_total = 0
        self.shots_made = 0

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        tx, tw = 140, 430
        self.angle_slider = Slider('angle', (tx, 552, tw, 12), "Angle", C.ANGLE_MIN, C.ANGLE_MAX, C.ANGLE_STEP,
                                   self.angle, lambda v: f"{v:.0f}{C.DEG}")
        self.vel_slider = Slider('velocity', (tx, 598, tw, 12), "Velocity", C.VEL_MIN, C.VEL_MAX, C.VEL_STEP,
                                 self.velocity, lambda v: f"{v:.1f} m/s")
        by, bh = 636, 50
        mid = C.WIDTH // 2
        B = Button
        self.buttons = {
            'shoot': B('shoot', (20, by, 150, bh), "SHOOT", C.BTN_GREEN, C.BTN_GREEN_HOVER, "SPACE"),
            'reset': B('reset', (180, by, 120, bh), "RESET", C.BTN_GREY, C.BTN_GREY_HOVER, "R"),
            'retry': B('retry', (310, by, 150, bh), "TRY AGAIN", C.BTN, C.BTN_HOVER, "SPACE"),
            'retry_level': B('retry_level', (310, by, 170, bh), "RETRY LEVEL", C.BTN, C.BTN_HOVER, "SPACE"),
            'next': B('next', (470, by, 160, bh), "NEXT LEVEL", C.BTN_ORANGE, C.BTN_ORANGE_HOVER, "N"),
            'pause': B('pause', (640, by, 110, bh), "PAUSE", C.BTN_GREY, C.BTN_GREY_HOVER, "P"),
            'howto': B('howto', (760, by, 115, bh), "HOW TO PLAY", C.BTN_GREY, C.BTN_GREY_HOVER, "H"),
            'levels': B('levels', (1052, 8, 100, 32), "LEVELS", C.BTN_GREY, C.BTN_GREY_HOVER),
            'menu': B('menu', (1162, 8, 100, 32), "MENU", C.BTN_GREY, C.BTN_GREY_HOVER),
            # Free Play environment controls
            'wind_minus': B('wind_minus', (676, 540, 36, 32), "-", C.BTN_GREY, C.BTN_GREY_HOVER),
            'wind_plus': B('wind_plus', (832, 540, 36, 32), "+", C.BTN_GREY, C.BTN_GREY_HOVER),
            'air': B('air', (676, 586, 192, 32), "AIR RESISTANCE: OFF", C.BTN_GREY, C.BTN_GREY_HOVER),
            # Menu
            'play': B('play', (mid - 130, 330, 260, 54), "PLAY", C.BTN_GREEN, C.BTN_GREEN_HOVER),
            'menu_howto': B('menu_howto', (mid - 130, 396, 260, 54), "HOW TO PLAY"),
            'menu_levels': B('menu_levels', (mid - 130, 462, 260, 54), "LEVEL SELECT"),
            'quit': B('quit', (mid - 130, 528, 260, 54), "QUIT", C.BTN_GREY, C.BTN_GREY_HOVER),
            # Tutorial / help
            'tut_start': B('tut_start', (mid - 140, 652, 280, 50), "START PLAYING", C.BTN_GREEN, C.BTN_GREEN_HOVER, "ENTER"),
            'tut_back': B('tut_back', (mid - 140, 652, 280, 50), "BACK", C.BTN, C.BTN_HOVER, "ESC"),
            # Level select
            'ls_back': B('ls_back', (mid - 100, 650, 200, 48), "MAIN MENU", C.BTN_GREY, C.BTN_GREY_HOVER, "ESC"),
            # Pause
            'resume': B('resume', (C.GAME_RECT.centerx - 110, 250, 220, 50), "RESUME", C.BTN_GREEN, C.BTN_GREEN_HOVER, "P"),
            'pause_howto': B('pause_howto', (C.GAME_RECT.centerx - 110, 312, 220, 50), "HOW TO PLAY", C.BTN, C.BTN_HOVER, "H"),
            'pause_levels': B('pause_levels', (C.GAME_RECT.centerx - 110, 374, 220, 50), "LEVEL SELECT", C.BTN_GREY, C.BTN_GREY_HOVER, "ESC"),
            # Game complete
            'gc_free': B('gc_free', (mid - 290, 620, 270, 52), "FREE PLAY LAB", C.BTN_ORANGE, C.BTN_ORANGE_HOVER),
            'gc_levels': B('gc_levels', (mid + 20, 620, 270, 52), "LEVEL SELECT", C.BTN, C.BTN_HOVER, "ENTER"),
        }
        self.level_cards = screens.level_card_rects(len(LEVELS))
        self.demo = DemoShot(screens.DEMO_RECT)

    def visible_buttons(self) -> List[Button]:
        b = self.buttons
        S = self.state
        if S == State.MENU:
            return [b['play'], b['menu_howto'], b['menu_levels'], b['quit']]
        if S == State.TUTORIAL:
            return [b['tut_start']]
        if S == State.HOW_TO_PLAY:
            return [b['tut_back']]
        if S == State.LEVEL_SELECT:
            return [b['ls_back']]
        if S == State.GAME_COMPLETE:
            return [b['gc_free'], b['gc_levels']]
        if S == State.PAUSED:
            return [b['resume'], b['pause_howto'], b['pause_levels'], b['levels'], b['menu']]
        lst = [b['levels'], b['menu'], b['howto']]
        if S == State.AIMING:
            lst += [b['shoot'], b['reset'], b['pause']]
            if self.level.allow_env_controls:
                lst += [b['wind_minus'], b['wind_plus'], b['air']]
        elif S == State.SHOOTING:
            lst += [b['pause']]
        elif S == State.RESULT:
            if self.result and self.result.level_failed:
                lst += [b['retry_level']]
            else:
                lst += [b['retry'], b['reset']]
                if self.result and self.result.made:
                    lst += [b['next']]
        return lst

    # --------------------------------------------------------------- states
    def set_state(self, state: State):
        self.state = state
        self.angle_slider.enabled = state == State.AIMING
        self.vel_slider.enabled = state == State.AIMING
        self.angle_slider.dragging = False
        self.vel_slider.dragging = False

    def go_to_menu(self):
        self.set_state(State.MENU)

    def go_to_level_select(self):
        self.set_state(State.LEVEL_SELECT)

    def show_help(self):
        if self.state != State.HOW_TO_PLAY:
            self.return_state = self.state
            self.set_state(State.HOW_TO_PLAY)

    def close_help(self):
        self.set_state(self.return_state if self.return_state != State.HOW_TO_PLAY else State.MENU)

    def pause(self):
        if self.state in (State.AIMING, State.SHOOTING, State.RESULT):
            self.return_state = self.state
            self.set_state(State.PAUSED)

    def resume(self):
        self.set_state(self.return_state)

    # --------------------------------------------------------------- levels
    def start_level(self, index: int, keep_aim: bool = False):
        self.level_index = index
        lv = LEVELS[index]
        self.level = lv
        self.hoop = Hoop(lv.hoop_x, lv.hoop_y, C.HOOP_WIDTH_M, lv.hoop_move_amplitude, lv.hoop_move_period)
        self.obstacles = [Obstacle(*o) for o in lv.obstacles]
        self.env = Environment()
        self.buttons['air'].text = "AIR RESISTANCE: OFF"
        self.attempts = 0
        self.shots_left = lv.max_shots
        self.level_score = 0
        self.level_time = 0.0
        self.ball = None
        self.result = None
        self.cross_x = None
        if self.session_start is None:
            self.session_start = time.time()
        if not keep_aim:
            self.angle_slider.set_value(C.DEFAULT_ANGLE)
            self.vel_slider.set_value(C.DEFAULT_VELOCITY)
        self.sync_aim()
        self.set_state(State.AIMING)

    def reset_level(self):
        """RESET: restart the current level (attempts, shots and sliders)."""
        self.start_level(self.level_index)

    def try_again(self):
        """TRY AGAIN: keep the slider settings, shoot again."""
        self.ball = None
        self.result = None
        self.cross_x = None
        self.set_state(State.AIMING)

    def next_level(self):
        lv = self.level
        if lv.number == MAIN_COURSE_COUNT and self.session_start is not None:
            self.course_time = time.time() - self.session_start
            if self.save.fastest_completion <= 0 or self.course_time < self.save.fastest_completion:
                self.save.fastest_completion = self.course_time
            self.save.save()
            self.set_state(State.GAME_COMPLETE)
            return
        nxt = self.level_index + 1
        if nxt < len(LEVELS) and nxt < self.save.unlocked:
            self.start_level(nxt)
        else:
            self.go_to_level_select()

    def unlock_all(self):
        self.save.unlocked = len(LEVELS)
        self.save.save()

    # ------------------------------------------------------------------ aim
    def sync_aim(self):
        self.angle = self.angle_slider.value
        self.velocity = self.vel_slider.value
        self.update_preview()

    def update_preview(self):
        if self.level is None:
            return
        lx, ly = self.level.launch
        self.preview = predict_flight(lx, ly, self.velocity, self.angle, self.env, 0.0, 0.02,
                                      x_limit=C.WORLD_WIDTH_M + 2)

    def adjust_wind(self, delta: float):
        self.env = Environment(self.env.g, round(max(-5.0, min(5.0, self.env.wind_ax + delta)), 1), self.env.drag_k)
        self.update_preview()

    def toggle_air(self):
        k = 0.0 if not self.env.is_ideal else BASKETBALL_DRAG_K
        self.env = Environment(self.env.g, self.env.wind_ax, k)
        self.buttons['air'].text = "AIR RESISTANCE: ON" if k > 0 else "AIR RESISTANCE: OFF"
        self.update_preview()

    # ---------------------------------------------------------------- shoot
    def shoot(self):
        if self.state != State.AIMING:
            return
        lx, ly = self.level.launch
        self.ball = Projectile(lx, ly, self.velocity, self.angle, self.env)
        self.cross_x = None
        self.physics_acc = 0.0
        self.shots_total += 1
        self.sounds.play('shoot')
        self.set_state(State.SHOOTING)

    def update_shooting(self, dt: float):
        self.physics_acc += dt * self.time_scale
        while self.physics_acc >= C.PHYSICS_STEP and self.state == State.SHOOTING:
            self.physics_acc -= C.PHYSICS_STEP
            self.step_physics(C.PHYSICS_STEP)

    def step_physics(self, h: float):
        """One fixed physics step: move the ball with the projectile equations, then check collisions."""
        self.level_time += h
        self.hoop.update(self.level_time)
        b = self.ball
        b.update(h)

        for ob in self.obstacles:
            if ob.collides_circle(b.x, b.y, b.radius):
                self.finish_shot('obstacle')
                return

        if self.hoop.hits_backboard(b):
            bx = self.hoop.backboard_rect()[0]
            b.rebase(bx - b.radius, b.y, -b.vx * C.BACKBOARD_RESTITUTION, b.vy)
            self.sounds.play('bounce')

        res, xc = self.hoop.check_scoring(b.prev_x, b.prev_y, b.x, b.y, b.radius)
        if res == 'made':
            self.finish_shot('made', xc)
            return
        if res == 'rim':
            self.cross_x = xc
            self.finish_shot('rim', xc)
            return
        if res == 'under':
            self.finish_shot('under', xc)
            return
        if res == 'passed' and self.cross_x is None:
            self.cross_x = xc

        if b.y - b.radius <= 0.0:
            self.finish_shot('ground')
            return
        if b.x - b.radius > C.WORLD_WIDTH_M + 1.5 or b.x + b.radius < 0 or b.elapsed > 40:
            self.finish_shot('out')

    def finish_shot(self, outcome: str, cross_x: Optional[float] = None):
        b = self.ball
        lv = self.level
        self.attempts += 1
        if self.shots_left is not None:
            self.shots_left -= 1
        made = outcome == 'made'
        breakdown = None
        offset = 0.0
        if made:
            self.streak += 1
            self.shots_made += 1
            offset = cross_x - self.hoop.x
            breakdown = calculate_score(offset, self.hoop.width / 2, self.attempts, self.streak)
            self.total_score += breakdown.total
            self.level_score += breakdown.total
            self.save.record_level_result(lv.number, self.level_score, self.attempts, breakdown.accuracy)
            if not lv.bonus:
                self.save.unlocked = max(self.save.unlocked, min(len(LEVELS), lv.number + 1))
            self.save.best_total = max(self.save.best_total, self.total_score)
            self.save.save()
            self.sounds.play('swish')
            self.sounds.play('score')
        else:
            self.streak = 0
            self.sounds.play('rim' if outcome == 'rim' else 'miss')

        distance = (cross_x if made else b.x) - b.launch_x
        ctx = ShotContext(
            outcome=outcome, angle=self.angle, velocity=self.velocity,
            launch_x=b.launch_x, launch_y=b.launch_y,
            hoop_x=self.hoop.x, hoop_y=self.hoop.y, hoop_half_width=self.hoop.width / 2,
            cross_x=cross_x if made else self.cross_x,
            max_height=b.max_height, landing_x=b.x, bounced=b.bounces > 0,
            attempts=self.attempts, give_numeric_hint=lv.show_preview, offset_m=offset,
        )
        fb = explain_result(ctx)
        level_failed = (not made) and self.shots_left == 0
        if level_failed:
            fb.title = "OUT OF SHOTS"
            fb.lines.append("Retry the level and use what you learned from each miss.")
        self.result = ShotResult(outcome, made, fb, breakdown, self.angle, self.velocity,
                                 b.elapsed, b.max_height, distance, level_failed)
        self.set_state(State.RESULT)

    # ---------------------------------------------------------------- input
    def on_button(self, name: str):
        actions = {
            'shoot': self.shoot, 'reset': self.reset_level, 'retry': self.try_again,
            'retry_level': self.reset_level, 'next': self.next_level, 'pause': self.pause,
            'howto': self.show_help, 'levels': self.go_to_level_select, 'menu': self.go_to_menu,
            'wind_minus': lambda: self.adjust_wind(-1.0), 'wind_plus': lambda: self.adjust_wind(1.0),
            'air': self.toggle_air,
            'play': self.on_play, 'menu_howto': self.show_help, 'menu_levels': self.go_to_level_select,
            'quit': self.quit, 'tut_start': self.finish_tutorial, 'tut_back': self.close_help,
            'ls_back': self.go_to_menu, 'resume': self.resume, 'pause_howto': self.show_help,
            'pause_levels': self.go_to_level_select, 'gc_free': lambda: self.start_level(len(LEVELS) - 1),
            'gc_levels': self.go_to_level_select,
        }
        action = actions.get(name)
        if action:
            action()

    def on_play(self):
        if self.save.seen_tutorial:
            self.go_to_level_select()
        else:
            self.set_state(State.TUTORIAL)

    def finish_tutorial(self):
        self.save.seen_tutorial = True
        self.save.save()
        self.go_to_level_select()

    def quit(self):
        self.running = False

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            self.handle_key(e.key, e.mod)
            return
        for btn in self.visible_buttons():
            if btn.handle_event(e):
                self.sounds.play('click')
                self.on_button(btn.name)
                return
        if self.state == State.AIMING:
            changed = self.angle_slider.handle_event(e)
            changed = self.vel_slider.handle_event(e) or changed
            if changed:
                self.sync_aim()
        elif self.state == State.LEVEL_SELECT and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, rect in enumerate(self.level_cards):
                if rect.collidepoint(e.pos) and i < self.save.unlocked:
                    self.sounds.play('click')
                    self.start_level(i)
                    return

    def handle_key(self, key, mod):
        S = self.state
        shift = bool(mod & pygame.KMOD_SHIFT)
        if key == pygame.K_ESCAPE:
            if S in PLAY_STATES:
                self.go_to_level_select()
            elif S == State.HOW_TO_PLAY:
                self.close_help()
            elif S in (State.TUTORIAL, State.LEVEL_SELECT, State.GAME_COMPLETE):
                self.go_to_menu()
            return
        if S == State.MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.on_play()
            elif key == pygame.K_h:
                self.show_help()
            elif key == pygame.K_l:
                self.go_to_level_select()
        elif S == State.TUTORIAL:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.finish_tutorial()
        elif S == State.HOW_TO_PLAY:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_h):
                self.close_help()
        elif S == State.LEVEL_SELECT:
            if key == pygame.K_u:
                self.unlock_all()
            elif pygame.K_1 <= key <= pygame.K_9:
                idx = key - pygame.K_1
                if idx < len(LEVELS) and idx < self.save.unlocked:
                    self.start_level(idx)
        elif S == State.GAME_COMPLETE:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.go_to_level_select()
        elif S == State.AIMING:
            if key == pygame.K_LEFT:
                self.angle_slider.nudge(-5 if shift else -1); self.sync_aim()
            elif key == pygame.K_RIGHT:
                self.angle_slider.nudge(5 if shift else 1); self.sync_aim()
            elif key == pygame.K_UP:
                self.vel_slider.nudge(10 if shift else 1); self.sync_aim()
            elif key == pygame.K_DOWN:
                self.vel_slider.nudge(-10 if shift else -1); self.sync_aim()
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.shoot()
            elif key == pygame.K_r:
                self.reset_level()
            elif key == pygame.K_p:
                self.pause()
            elif key == pygame.K_h:
                self.show_help()
            elif key == pygame.K_v:
                self.show_vectors = not self.show_vectors
            elif key == pygame.K_s:
                self.time_scale = 0.25 if self.time_scale >= 1.0 else 1.0
        elif S == State.SHOOTING:
            if key == pygame.K_p:
                self.pause()
            elif key == pygame.K_v:
                self.show_vectors = not self.show_vectors
            elif key == pygame.K_s:
                self.time_scale = 0.25 if self.time_scale >= 1.0 else 1.0
            elif key == pygame.K_h:
                self.show_help()
        elif S == State.RESULT:
            r = self.result
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                if r.level_failed:
                    self.reset_level()
                elif r.made:
                    self.next_level()
                else:
                    self.try_again()
            elif key == pygame.K_n and r.made:
                self.next_level()
            elif key == pygame.K_r:
                self.reset_level()
            elif key == pygame.K_h:
                self.show_help()
            elif key == pygame.K_v:
                self.show_vectors = not self.show_vectors
        elif S == State.PAUSED:
            if key in (pygame.K_p, pygame.K_SPACE, pygame.K_RETURN):
                self.resume()
            elif key == pygame.K_h:
                self.show_help()

    # --------------------------------------------------------------- update
    def update(self, dt: float):
        if self.state in (State.MENU, State.TUTORIAL, State.HOW_TO_PLAY):
            self.demo.update(dt)
        if self.state in (State.AIMING, State.RESULT):
            if self.hoop is not None and self.hoop.moving:
                self.level_time += dt
                self.hoop.update(self.level_time)
        if self.state == State.SHOOTING:
            self.update_shooting(dt)

    # ----------------------------------------------------------------- draw
    def draw(self):
        s = self.screen
        R = self.renderer
        S = self.state
        if S == State.MENU:
            screens.draw_menu(s, R, self)
        elif S == State.TUTORIAL or (S == State.HOW_TO_PLAY and self.return_state not in PLAY_STATES):
            screens.draw_tutorial(s, R, self)
        elif S == State.LEVEL_SELECT:
            screens.draw_level_select(s, R, self)
        elif S == State.GAME_COMPLETE:
            screens.draw_game_complete(s, R, self)
        else:
            self.draw_play_screen()
            if S == State.HOW_TO_PLAY:
                R.draw_dim(s, pygame.Rect(0, 0, C.WIDTH, C.HEIGHT), 240)
                screens.draw_tutorial(s, R, self, background=False)
        for btn in self.visible_buttons():
            btn.draw(s, self.fonts['btn'], self.fonts['tiny'])
        pygame.display.flip()

    def draw_play_screen(self):
        s = self.screen
        R = self.renderer
        lv = self.level
        R.draw_header(s, self)
        R.draw_court(s)
        R.draw_obstacles(s, self.obstacles)
        R.draw_hoop(s, self.hoop)
        # trajectory preview (prediction) - kept visible during the shot so prediction and reality can be compared
        mode = "full" if lv.show_preview else "stub"
        if self.state == State.AIMING or lv.show_preview:
            R.draw_preview(s, self.preview, mode, labels=(self.state == State.AIMING))
        R.draw_launcher(s, lv.launch, self.angle)
        if self.ball is not None:
            R.draw_trail(s, self.ball)
            R.draw_ball(s, self.ball.x, self.ball.y, self.ball.spin)
            if self.show_vectors and self.state in (State.SHOOTING, State.PAUSED):
                R.draw_velocity_vectors(s, self.ball.x, self.ball.y, self.ball.vx, self.ball.vy)
            R.draw_offscreen_marker(s, self.ball)
        else:
            lx, ly = lv.launch
            R.draw_ball(s, lx, ly, 0.0)
            if self.show_vectors and self.state == State.AIMING:
                from .physics import calculate_velocity_components
                vx, vy = calculate_velocity_components(self.velocity, self.angle)
                R.draw_velocity_vectors(s, lx, ly, vx, vy)
        R.draw_controls(s, self)
        R.draw_panel(s, self)
        if self.state == State.RESULT:
            R.draw_result_overlay(s, self)
        elif self.state == State.PAUSED:
            R.draw_dim(s, C.GAME_RECT)
            screens.draw_pause(s, R, self)

    # ------------------------------------------------------------------ loop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 1.0 / 20.0)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
        pygame.quit()


def main():
    Game().run()
