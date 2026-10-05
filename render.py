"""
render.py - All drawing for Physics Hoops.

The Renderer knows how to draw the court, launcher, hoop, ball, trajectory
preview, information panel and overlays.  It reads state from the Game object
but never changes it.
"""
from __future__ import annotations

import math
from typing import Callable, Optional, Tuple

import pygame

from . import config as C
from .entities import Hoop, Obstacle, Projectile
from .physics import FlightPrediction, calculate_velocity_components
from .ui import draw_arrow, draw_box, draw_text, draw_wrapped, wrap_text

VECTOR_SCALE_M_PER_MS = 0.12   # arrow length in metres for 1 m/s of velocity


class Renderer:
    def __init__(self):
        self.fonts = self._load_fonts()
        self.sky = self._build_sky()
        self.ball_sprite = self._build_ball_sprite(int(C.m_to_px(C.BALL_RADIUS_M)))
        self.sprite_cache = {}

    # ------------------------------------------------------------------ setup
    @staticmethod
    def _load_fonts():
        def f(size, bold=False, mono=False):
            name = "consolas,couriernew,dejavusansmono" if mono else "segoeui,arial,helvetica,dejavusans"
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                font = pygame.font.Font(None, int(size * 1.3))
                font.set_bold(bold)
                return font

        return {
            'title': f(26, True), 'h1': f(38, True), 'h2': f(20, True), 'h3': f(17, True),
            'body': f(16), 'small': f(13), 'tiny': f(11), 'btn': f(16, True),
            'mono': f(15, mono=True), 'mono_b': f(17, True, True), 'big': f(54, True), 'huge': f(72, True),
        }

    @staticmethod
    def _build_sky():
        surf = pygame.Surface(C.GAME_RECT.size)
        h = C.GAME_RECT.height
        for row in range(h):
            t = row / max(1, h - 1)
            col = tuple(int(C.SKY_TOP[i] + (C.SKY_BOTTOM[i] - C.SKY_TOP[i]) * t) for i in range(3))
            pygame.draw.line(surf, col, (0, row), (C.GAME_RECT.width, row))
        return surf

    @staticmethod
    def _build_ball_sprite(r: int):
        size = r * 2 + 6
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        pygame.draw.circle(surf, C.BALL_ORANGE, (c, c), r)
        pygame.draw.line(surf, C.BALL_SEAM, (c - r, c), (c + r, c), 2)
        pygame.draw.line(surf, C.BALL_SEAM, (c, c - r), (c, c + r), 2)
        pygame.draw.ellipse(surf, C.BALL_SEAM, pygame.Rect(c - int(r * 0.45), c - r, int(r * 0.9), 2 * r), 2)
        pygame.draw.circle(surf, C.BALL_SEAM, (c, c), r, 2)
        return surf

    def ball_sprite_for(self, r: int):
        if r not in self.sprite_cache:
            self.sprite_cache[r] = self._build_ball_sprite(r)
        return self.sprite_cache[r]

    # --------------------------------------------------------------- world
    def draw_court(self, s):
        s.blit(self.sky, C.GAME_RECT.topleft)
        floor = pygame.Rect(C.GAME_RECT.x, C.GROUND_SCREEN_Y, C.GAME_RECT.width, C.GAME_RECT.bottom - C.GROUND_SCREEN_Y)
        pygame.draw.rect(s, C.FLOOR, floor)
        for px in range(C.GAME_RECT.x, C.GAME_RECT.right, 56):
            pygame.draw.line(s, C.FLOOR_DARK, (px, C.GROUND_SCREEN_Y), (px, C.GAME_RECT.bottom), 1)
        pygame.draw.line(s, C.FLOOR_LINE, (C.GAME_RECT.x, C.GROUND_SCREEN_Y), (C.GAME_RECT.right, C.GROUND_SCREEN_Y), 3)
        # Distance ruler on the floor (metres)
        for m in range(0, int(C.WORLD_WIDTH_M) + 1):
            sx, sy = C.world_to_screen(m, 0)
            if m % 5 == 0:
                pygame.draw.line(s, C.FLOOR_LINE, (sx, sy), (sx, sy + 10), 2)
                draw_text(s, f"{m} m", (sx, sy + 13), self.fonts['tiny'], C.FLOOR_LINE, "midtop")
            else:
                pygame.draw.line(s, C.FLOOR_LINE, (sx, sy), (sx, sy + 5), 1)
        # Height ruler on the right edge
        for h in range(2, int(C.WORLD_TOP_M) + 1, 2):
            sx, sy = C.world_to_screen(C.WORLD_WIDTH_M, h)
            pygame.draw.line(s, (200, 210, 230), (C.GAME_RECT.right - 8, sy), (C.GAME_RECT.right, sy), 1)
            draw_text(s, f"{h} m", (C.GAME_RECT.right - 11, sy), self.fonts['tiny'], (200, 210, 230), "midright")

    def draw_launcher(self, s, launch: Tuple[float, float], angle_deg: float, w2s=None):
        w2s = w2s or C.world_to_screen
        lx, ly = launch
        th = math.radians(angle_deg)
        length = 0.9
        bx, by = w2s(lx, ly)
        mx, my = lx - 0.5 * length * math.cos(th), ly - 0.5 * length * math.sin(th)
        px, py = lx - length * math.cos(th), ly - length * math.sin(th)
        smx, smy = w2s(mx, my)
        spx, spy = w2s(px, py)
        # pedestal column + base
        gx, gy = w2s(mx, 0)
        pygame.draw.rect(s, C.POLE, pygame.Rect(int(gx - 7), int(smy), 14, int(gy - smy)))
        pygame.draw.rect(s, (90, 95, 110), pygame.Rect(int(gx - 24), int(gy - 8), 48, 8), border_radius=3)
        # barrel
        pygame.draw.line(s, (60, 64, 80), (spx, spy), (bx, by), 22)
        pygame.draw.line(s, (120, 130, 160), (spx, spy), (bx, by), 14)
        pygame.draw.circle(s, (80, 86, 108), (int(smx), int(smy)), 11)
        pygame.draw.circle(s, (0, 0, 0), (int(smx), int(smy)), 11, 2)
        # angle indicator: horizontal reference and arc
        ref_len = 60
        pygame.draw.line(s, (255, 255, 255), (spx, spy), (spx + ref_len, spy), 1)
        arc_rect = pygame.Rect(int(spx - 44), int(spy - 44), 88, 88)
        pygame.draw.arc(s, C.GOLD, arc_rect, 0, th, 2)
        draw_text(s, f"{angle_deg:.0f}{C.DEG}", (spx + 34, spy + 4), self.fonts['small'], C.GOLD, "midtop")

    def draw_obstacles(self, s, obstacles):
        for ob in obstacles:
            x0, y0 = C.world_to_screen(ob.x, ob.top)
            x1, y1 = C.world_to_screen(ob.right, ob.y)
            rect = pygame.Rect(int(x0), int(y0), int(x1 - x0), int(y1 - y0))
            pygame.draw.rect(s, C.OBSTACLE, rect)
            # brick pattern
            row_h = 12
            row = 0
            for yy in range(rect.top, rect.bottom, row_h):
                pygame.draw.line(s, C.OBSTACLE_EDGE, (rect.left, yy), (rect.right, yy), 1)
                offset = 10 if row % 2 else 0
                for xx in range(rect.left + offset, rect.right, 20):
                    pygame.draw.line(s, C.OBSTACLE_EDGE, (xx, yy), (xx, min(yy + row_h, rect.bottom)), 1)
                row += 1
            pygame.draw.rect(s, C.OBSTACLE_EDGE, rect, 2)
            draw_text(s, f"{ob.h:.0f} m", (rect.centerx, rect.top - 4), self.fonts['tiny'], C.TEXT, "midbottom")

    def draw_hoop(self, s, hoop: Hoop, w2s=None, scale: float = C.PX_PER_M, show_range: bool = True):
        w2s = w2s or C.world_to_screen
        rim_w = max(3, int(0.08 * scale))
        lx, ly = w2s(hoop.left, hoop.y)
        rx, ry = w2s(hoop.right, hoop.y)
        # motion range ghost
        if hoop.moving and show_range:
            for gx in (hoop.base_x - hoop.move_amplitude, hoop.base_x + hoop.move_amplitude):
                g0 = w2s(gx - hoop.width / 2, hoop.y)
                g1 = w2s(gx + hoop.width / 2, hoop.y)
                pygame.draw.line(s, (255, 255, 255), g0, g1, 1)
            draw_text(s, "hoop moves between these marks", (w2s(hoop.base_x, hoop.y + 0.35)[0], ly - 6),
                      self.fonts['tiny'], (220, 220, 240), "midbottom")
        # backboard + pole
        bx, by, bw, bh = hoop.backboard_rect()
        b0 = w2s(bx, by + bh)
        b1 = w2s(bx + bw, by)
        board = pygame.Rect(int(b0[0]), int(b0[1]), max(3, int(b1[0] - b0[0])), int(b1[1] - b0[1]))
        pole_x = board.centerx
        ground_y = w2s(0, 0)[1]
        pygame.draw.rect(s, C.POLE, pygame.Rect(pole_x - max(2, int(0.1 * scale) // 2), board.bottom,
                                                 max(4, int(0.1 * scale)), int(ground_y - board.bottom)))
        pygame.draw.rect(s, C.BACKBOARD, board)
        pygame.draw.rect(s, C.BACKBOARD_LINE, board.inflate(-board.width // 2, -int(board.height * 0.55)), 2)
        # net
        depth = hoop.NET_DEPTH * scale
        n = 7
        bottom_shrink = 0.22
        for i in range(n + 1):
            f = i / n
            tx = lx + (rx - lx) * f
            bxn = lx + (rx - lx) * (bottom_shrink + f * (1 - 2 * bottom_shrink))
            pygame.draw.line(s, C.NET, (tx, ly), (bxn, ly + depth), 1)
        for j in range(1, 4):
            f = j / 4
            yy = ly + depth * f
            shrink = bottom_shrink * f
            pygame.draw.line(s, C.NET, (lx + (rx - lx) * shrink, yy), (rx - (rx - lx) * shrink, yy), 1)
        # rim (connect to backboard)
        pygame.draw.line(s, C.RIM, (rx, ry), (board.left, ry), rim_w)
        pygame.draw.line(s, C.RIM, (lx, ly), (rx, ry), rim_w)
        pygame.draw.circle(s, C.RIM, (int(lx), int(ly)), rim_w)
        pygame.draw.circle(s, C.RIM, (int(rx), int(ry)), rim_w)

    def draw_ball(self, s, x: float, y: float, spin: float = 0.0, w2s=None, radius_m: float = C.BALL_RADIUS_M,
                  scale: float = C.PX_PER_M):
        w2s = w2s or C.world_to_screen
        sx, sy = w2s(x, y)
        sprite = self.ball_sprite_for(int(radius_m * scale))
        img = pygame.transform.rotozoom(sprite, -math.degrees(spin), 1.0)
        rect = img.get_rect(center=(int(sx), int(sy)))
        s.blit(img, rect)

    def draw_velocity_vectors(self, s, x, y, vx, vy, w2s=None, scale: float = C.PX_PER_M, labels: bool = True):
        """Draw Vx (blue), Vy (green) and the resultant velocity (red) as arrows from the ball."""
        w2s = w2s or C.world_to_screen
        sx, sy = w2s(x, y)
        k = VECTOR_SCALE_M_PER_MS * scale
        ex, ey = sx + vx * k, sy - vy * k
        if abs(vx) > 0.05:
            draw_arrow(s, (sx, sy), (sx + vx * k, sy), C.ACCENT, 3, 9)
        if abs(vy) > 0.05:
            draw_arrow(s, (sx, sy), (sx, sy - vy * k), C.ACCENT2, 3, 9)
        draw_arrow(s, (sx, sy), (ex, ey), C.ACCENT3, 2, 9)
        if labels:
            f = self.fonts['tiny']
            if abs(vx) * k > 12:
                draw_text(s, f"Vx {vx:.1f}", (sx + vx * k + 4, sy + 2), f, C.ACCENT, "midleft")
            if abs(vy) * k > 14:
                tip_y = sy - vy * k
                draw_text(s, f"Vy {vy:+.1f}", (sx + 6, tip_y - 8 if vy > 0 else tip_y + 8), f, C.ACCENT2, "midleft")

    def draw_preview(self, s, pred: FlightPrediction, mode: str = "full", w2s=None, scale: float = C.PX_PER_M,
                     clip=None, color=C.PREVIEW, labels: bool = True):
        """Dotted predicted path. mode: 'full' (dots + apex + landing), 'stub' (first 0.3 s only), 'none'."""
        if mode == "none" or pred is None:
            return
        w2s = w2s or C.world_to_screen
        clip = clip or C.GAME_RECT
        overlay = pygame.Surface(clip.size, pygame.SRCALPHA)
        ox, oy = clip.topleft
        pts = pred.points
        if mode == "stub":
            pts = [p for p in pts if p[0] <= 0.3]
            step = 2
        else:
            step = 4
        n = len(pts)
        for i in range(0, n, step):
            t, x, y = pts[i]
            sx, sy = w2s(x, y)
            alpha = 230 if mode == "stub" else int(220 - 120 * (i / max(1, n)))
            r = 3 if mode == "full" else 2
            if 0 <= sx - ox <= clip.width and -20 <= sy - oy <= clip.height:
                pygame.draw.circle(overlay, (*color[:3], max(40, alpha)), (int(sx - ox), int(sy - oy)), r)
        s.blit(overlay, clip.topleft)
        if mode == "full" and labels:
            ax, ay = pred.apex
            asx, asy = w2s(ax, ay)
            if clip.top <= asy <= clip.bottom and clip.left <= asx <= clip.right:
                pygame.draw.line(s, C.GOLD, (asx - 8, asy), (asx + 8, asy), 2)
                draw_text(s, f"max height {pred.max_height:.1f} m", (asx, asy - 6), self.fonts['tiny'], C.GOLD, "midbottom")
            elif asy < clip.top and clip.left <= asx <= clip.right:
                draw_text(s, f"apex {pred.max_height:.1f} m (off screen)", (asx, clip.top + 4), self.fonts['tiny'], C.GOLD, "midtop")
            lsx, lsy = w2s(pred.landing_x, 0)
            if clip.left <= lsx <= clip.right:
                pygame.draw.line(s, C.ACCENT3, (lsx - 7, lsy - 7), (lsx + 7, lsy + 7), 2)
                pygame.draw.line(s, C.ACCENT3, (lsx - 7, lsy + 7), (lsx + 7, lsy - 7), 2)
                draw_text(s, f"range {pred.range:.1f} m", (lsx, lsy - 10), self.fonts['tiny'], C.ACCENT3, "midbottom")

    def draw_trail(self, s, ball: Projectile):
        for (x, y) in ball.trail:
            sx, sy = C.world_to_screen(x, y)
            if C.GAME_RECT.collidepoint(sx, sy):
                pygame.draw.circle(s, C.TRAIL, (int(sx), int(sy)), 2)

    def draw_offscreen_marker(self, s, ball: Projectile):
        sx, sy = C.world_to_screen(ball.x, ball.y)
        if sy < C.GAME_RECT.top + 6 and C.GAME_RECT.left <= sx <= C.GAME_RECT.right:
            top = C.GAME_RECT.top + 8
            pygame.draw.polygon(s, C.BALL_ORANGE, [(sx, top), (sx - 10, top + 16), (sx + 10, top + 16)])
            draw_text(s, f"ball at {ball.y:.1f} m", (sx, top + 18), self.fonts['tiny'], C.TEXT, "midtop")

    # ---------------------------------------------------------------- panels
    def _row(self, s, label, value, y, x0, x1, label_color=C.TEXT_DIM, value_color=C.TEXT, font=None):
        font = font or self.fonts['body']
        draw_text(s, label, (x0, y), font, label_color)
        draw_text(s, value, (x1, y), self.fonts['mono'], value_color, "topright")
        return y + font.get_linesize()

    def _section(self, s, rect, title):
        draw_box(s, rect, C.PANEL_BOX, C.PANEL_EDGE)
        draw_text(s, title, (rect.x + 12, rect.y + 8), self.fonts['h3'], C.GOLD)
        pygame.draw.line(s, C.PANEL_EDGE, (rect.x + 12, rect.y + 32), (rect.right - 12, rect.y + 32), 1)
        return rect.y + 40

    def draw_panel(self, s, game):
        pygame.draw.rect(s, C.PANEL_BG, C.PANEL_RECT)
        P = C.PANEL_RECT
        x0, x1 = P.x + 14, P.right - 14
        lv = game.level
        f = self.fonts

        # Level box
        box = pygame.Rect(P.x + 6, P.y + 8, P.width - 12, 104)
        y = self._section(s, box, f"LEVEL {lv.number} - {lv.name}")
        y = draw_wrapped(s, lv.subtitle, (x0, y), f['small'], C.TEXT, box.width - 28)
        if game.shots_left is not None:
            col = C.ACCENT3 if game.shots_left <= 1 else C.TEXT
            draw_text(s, f"Shots remaining: {game.shots_left}", (x0, y + 2), f['body'], col)
        else:
            draw_text(s, "Unlimited shots", (x0, y + 2), f['body'], C.TEXT)
        draw_text(s, f"Attempts: {game.attempts}", (x1, y + 2), f['body'], C.TEXT_DIM, "topright")

        # Score box
        box = pygame.Rect(P.x + 6, box.bottom + 8, P.width - 12, 70)
        draw_box(s, box, C.PANEL_BOX, C.PANEL_EDGE)
        draw_text(s, "SCORE", (x0, box.y + 10), f['h3'], C.GOLD)
        draw_text(s, f"{game.total_score}", (x0, box.y + 30), f['big'] if False else f['h1'], C.WHITE)
        draw_text(s, f"Streak: {game.streak}", (x1, box.y + 12), f['body'], C.TEXT, "topright")
        best = game.save.best_level_scores.get(str(lv.number), 0)
        draw_text(s, f"Level best: {best}", (x1, box.y + 36), f['small'], C.TEXT_DIM, "topright")

        # Physics box
        box = pygame.Rect(P.x + 6, box.bottom + 8, P.width - 12, 336)
        self._draw_physics_box(s, box, game, x0, x1)

        # Tip / feedback box
        box = pygame.Rect(P.x + 6, box.bottom + 8, P.width - 12, P.bottom - box.bottom - 16)
        if game.result is not None:
            y = self._section(s, box, "WHAT HAPPENED")
            fb = game.result.feedback
            y = draw_wrapped(s, fb.headline, (x0, y), f['small'], C.TEXT, box.width - 28)
            if fb.hint:
                y = draw_wrapped(s, "Tip: " + fb.hint, (x0, y + 4), f['small'], C.GOLD, box.width - 28)
        else:
            y = self._section(s, box, "TIP")
            draw_wrapped(s, lv.tip, (x0, y), f['small'], C.TEXT, box.width - 28)

    def _draw_physics_box(self, s, box, game, x0, x1):
        f = self.fonts
        lv = game.level
        state = game.state.name
        ball = game.ball
        if state in ("SHOOTING", "PAUSED", "HOW_TO_PLAY") and ball is not None and game.result is None:
            y = self._section(s, box, "LIVE SHOT (physics in action)")
            y = self._row(s, "Time", f"{ball.elapsed:.2f} s", y, x0, x1)
            y = self._row(s, "X position", f"{ball.x:.1f} m", y, x0, x1)
            y = self._row(s, "Y position (height)", f"{ball.y:.1f} m", y, x0, x1)
            y += 6
            y = self._row(s, "Horizontal velocity", f"{ball.vx:.2f} m/s", y, x0, x1, value_color=C.ACCENT)
            note = "constant: nothing pushes sideways" if game.env.is_ideal and game.env.wind_ax == 0 else "changed by wind / air"
            draw_text(s, note, (x0, y), f['tiny'], C.TEXT_DIM)
            y += 16
            trend = "rising" if ball.vy > 0.05 else ("falling" if ball.vy < -0.05 else "at the top")
            y = self._row(s, "Vertical velocity", f"{ball.vy:+.2f} m/s ({trend})", y, x0, x1, value_color=C.ACCENT2)
            lost = game.env.g * ball.elapsed
            draw_text(s, f"gravity has removed g x t = {lost:.1f} m/s of upward speed", (x0, y), f['tiny'], C.TEXT_DIM)
            y += 18
            y = self._row(s, "Speed", f"{ball.speed:.2f} m/s", y, x0, x1, value_color=C.ACCENT3)
            y = self._row(s, "Max height so far", f"{ball.max_height:.2f} m", y, x0, x1)
            y = self._row(s, "Distance so far", f"{ball.x - ball.launch_x:.2f} m", y, x0, x1)
            if ball.bounces:
                draw_text(s, "Bounced off the backboard - equations restarted with the new velocity",
                          (x0, y + 4), f['tiny'], C.GOLD)
            return

        if state == "RESULT" and game.result is not None:
            r = game.result
            y = self._section(s, box, "SHOT RESULTS")
            y = self._row(s, "Launch angle", f"{r.angle:.0f}{C.DEG}", y, x0, x1)
            y = self._row(s, "Initial velocity", f"{r.velocity:.1f} m/s", y, x0, x1)
            y = self._row(s, "Time of flight", f"{r.flight_time:.2f} s", y, x0, x1)
            y = self._row(s, "Maximum height", f"{r.max_height:.2f} m", y, x0, x1)
            label = "Horizontal distance to hoop" if r.made else "Horizontal distance travelled"
            y = self._row(s, label, f"{r.distance:.2f} m", y, x0, x1)
            y += 8
            if r.breakdown is not None:
                b = r.breakdown
                y = self._row(s, "Made shot", f"+{b.base}", y, x0, x1, value_color=C.ACCENT2)
                y = self._row(s, "Accuracy bonus", f"+{b.accuracy}", y, x0, x1, value_color=C.ACCENT2)
                y = self._row(s, "Efficiency bonus", f"+{b.efficiency}", y, x0, x1, value_color=C.ACCENT2)
                y = self._row(s, "Streak bonus", f"+{b.streak}", y, x0, x1, value_color=C.ACCENT2)
                y = self._row(s, "TOTAL", f"+{b.total}", y, x0, x1, label_color=C.GOLD, value_color=C.GOLD, font=f['h3'])
            else:
                draw_wrapped(s, "No points this time. Read the explanation below and adjust your shot.",
                             (x0, y), f['small'], C.TEXT_DIM, box.width - 28)
            return

        # AIMING (and anything else): planned shot
        y = self._section(s, box, "PROJECTILE MOTION")
        vx, vy = calculate_velocity_components(game.velocity, game.angle)
        y = self._row(s, "Angle", f"{game.angle:.0f}{C.DEG}", y, x0, x1, value_color=C.GOLD)
        y = self._row(s, "Initial velocity (V0)", f"{game.velocity:.1f} m/s", y, x0, x1, value_color=C.GOLD)
        y = self._row(s, "Gravity (g)", f"{game.env.g:.2f} m/s{C.SQ}", y, x0, x1)
        if game.env.wind_ax != 0:
            direction = "to the right" if game.env.wind_ax > 0 else "to the left"
            y = self._row(s, "Wind acceleration", f"{abs(game.env.wind_ax):.1f} m/s{C.SQ} {direction}", y, x0, x1, value_color=C.ACCENT3)
        if not game.env.is_ideal:
            y = self._row(s, "Air resistance", "ON (numerical)", y, x0, x1, value_color=C.ACCENT3)
        y += 4
        y = self._row(s, "Horizontal velocity  Vx = V0 cos", f"{vx:.2f} m/s", y, x0, x1, value_color=C.ACCENT)
        y = self._row(s, "Vertical velocity  Vy = V0 sin", f"{vy:.2f} m/s", y, x0, x1, value_color=C.ACCENT2)
        y += 4
        pred = game.preview
        if lv.show_estimates and pred is not None:
            y = self._row(s, "Estimated flight time", f"{pred.flight_time:.2f} s", y, x0, x1)
            y = self._row(s, "Estimated max height", f"{pred.max_height:.2f} m", y, x0, x1)
            y = self._row(s, "Estimated range", f"{pred.range:.1f} m", y, x0, x1)
            draw_text(s, "(to the ground, with no obstacles)", (x0, y), f['tiny'], C.TEXT_DIM)
            y += 16
        else:
            draw_text(s, "Estimates hidden in Advanced Mode - predict them yourself!", (x0, y), f['tiny'], C.ACCENT3)
            y += 18
        lx, ly = lv.launch
        hoop = game.hoop
        y += 2
        y = self._row(s, "Hoop distance (horizontal)", f"{hoop.x - lx:.1f} m", y, x0, x1, value_color=C.GOLD)
        y = self._row(s, "Hoop height above launch", f"{hoop.y - ly:+.2f} m", y, x0, x1, value_color=C.GOLD)

    # ------------------------------------------------------------- controls
    def draw_controls(self, s, game):
        pygame.draw.rect(s, C.CONTROL_BG, C.CONTROL_RECT)
        pygame.draw.line(s, C.PANEL_EDGE, C.CONTROL_RECT.topleft, C.CONTROL_RECT.topright, 2)
        game.angle_slider.draw(s, self.fonts['h3'], self.fonts['mono_b'])
        game.vel_slider.draw(s, self.fonts['h3'], self.fonts['mono_b'])
        f = self.fonts['tiny']
        hint = ("Keys: Left/Right = angle   Up/Down = velocity   (hold Shift for bigger steps)   "
                "SPACE = shoot   R = reset   P = pause   V = velocity arrows   S = slow motion   H = help")
        draw_text(s, hint, (C.CONTROL_RECT.centerx, C.CONTROL_RECT.bottom - 8), f, C.TEXT_DIM, "midbottom")
        if game.level is not None and game.level.allow_env_controls:
            draw_text(s, f"Wind {game.env.wind_ax:+.1f} m/s{C.SQ}", (772, 556), self.fonts['small'], C.TEXT, "center")
        if game.time_scale < 1.0:
            draw_text(s, "SLOW MOTION", (C.CONTROL_RECT.right - 16, C.CONTROL_RECT.top + 8), self.fonts['h3'], C.GOLD, "topright")

    def draw_header(self, s, game):
        pygame.draw.rect(s, C.HEADER_BG, C.HEADER_RECT)
        draw_text(s, "PHYSICS HOOPS", (16, C.HEADER_RECT.centery), self.fonts['title'], C.ORANGE, "midleft")
        draw_text(s, "A Projectile Motion Challenge", (236, C.HEADER_RECT.centery + 1), self.fonts['small'], C.TEXT_DIM, "midleft")
        state_label = {"AIMING": "AIMING - adjust the sliders", "SHOOTING": "SHOOTING - physics running",
                       "RESULT": "RESULT", "PAUSED": "PAUSED", "HOW_TO_PLAY": "HOW TO PLAY"}.get(game.state.name, "")
        draw_text(s, state_label, (640, C.HEADER_RECT.centery), self.fonts['h3'], C.TEXT, "center")
        flags = []
        flags.append("vectors ON" if game.show_vectors else "vectors OFF")
        if game.time_scale < 1.0:
            flags.append("slow-mo")
        draw_text(s, "   ".join(flags), (1030, C.HEADER_RECT.centery), self.fonts['tiny'], C.TEXT_DIM, "midright")

    # ------------------------------------------------------------- overlays
    def draw_result_overlay(self, s, game):
        r = game.result
        if r is None:
            return
        f = self.fonts
        w = 560
        inner = w - 40
        title_col = C.ACCENT2 if r.made else C.ACCENT3
        if r.level_failed:
            title_col = C.ACCENT3
        body_lines = []
        for text in [r.feedback.headline] + r.feedback.lines:
            body_lines += wrap_text(text, f['body'], inner)
        score_lines = []
        if r.breakdown is not None:
            b = r.breakdown
            score_lines = [f"+{b.base} POINTS", f"Accuracy Bonus: +{b.accuracy}",
                           f"Efficiency Bonus: +{b.efficiency}"]
            if b.streak:
                score_lines.append(f"Streak Bonus: +{b.streak}")
            score_lines.append(f"TOTAL: +{b.total}")
        hint_lines = wrap_text("Tip: " + r.feedback.hint, f['body'], inner) if r.feedback.hint else []
        lh = f['body'].get_linesize() + 2
        h = 70 + lh * (len(body_lines) + len(score_lines) + len(hint_lines)) + (14 if score_lines else 0) + (10 if hint_lines else 0) + 34
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (C.GAME_RECT.centerx, C.GAME_RECT.centery - 10)
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill((14, 16, 28, 225))
        s.blit(shade, rect.topleft)
        pygame.draw.rect(s, title_col, rect, 3, border_radius=12)
        y = rect.y + 14
        draw_text(s, r.feedback.title, (rect.centerx, y), f['h1'], title_col, "midtop")
        y += 50
        for line in body_lines:
            draw_text(s, line, (rect.x + 20, y), f['body'], C.TEXT)
            y += lh
        if score_lines:
            y += 8
            for i, line in enumerate(score_lines):
                col = C.GOLD if i == len(score_lines) - 1 else C.ACCENT2
                font = f['h3'] if i == len(score_lines) - 1 else f['body']
                draw_text(s, line, (rect.centerx, y), font, col, "midtop")
                y += lh
            y += 6
        if hint_lines:
            y += 4
            for line in hint_lines:
                draw_text(s, line, (rect.x + 20, y), f['body'], C.GOLD)
                y += lh
        prompt = ("Press SPACE to retry the level" if r.level_failed else
                  ("N or SPACE = next level,  R = replay this level" if r.made else "SPACE = try again"))
        draw_text(s, prompt, (rect.centerx, rect.bottom - 10), f['small'], C.TEXT_DIM, "midbottom")

    def draw_dim(self, s, rect, alpha=170):
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill((10, 12, 20, alpha))
        s.blit(shade, rect.topleft)
