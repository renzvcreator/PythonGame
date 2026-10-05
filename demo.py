"""
demo.py - A small self-playing shot used on the menu and tutorial screens.

It uses exactly the same Projectile / Hoop classes and physics functions as
the real game, so the tutorial picture is a live simulation, not a drawing.
"""
from __future__ import annotations

import pygame

from . import config as C
from .entities import Hoop, Projectile
from .physics import Environment, calculate_required_velocity, predict_flight
from .ui import draw_arrow, draw_text


class DemoShot:
    def __init__(self, rect, angles=(35, 45, 60), hoop=(9.0, 3.05), launch=(1.0, 1.0)):
        self.rect = pygame.Rect(rect)
        self.scale = self.rect.width / 12.0            # 12 m wide mini-court
        self.ground_y = self.rect.bottom - 22
        self.angles = angles
        self.index = 0
        self.launch = launch
        self.hoop = Hoop(hoop[0], hoop[1], width=1.1)
        self.env = Environment()
        self.ball = None
        self.pred = None
        self.done = False
        self.wait = 0.0
        self.made = False
        self.start()

    def w2s(self, x, y):
        return (self.rect.x + x * self.scale, self.ground_y - y * self.scale)

    def start(self):
        self.angle = self.angles[self.index % len(self.angles)]
        v = calculate_required_velocity(self.launch[0], self.launch[1], self.hoop.x, self.hoop.y, self.angle) or 9.0
        self.velocity = v
        self.ball = Projectile(self.launch[0], self.launch[1], v, self.angle, self.env, radius=0.3)
        self.pred = predict_flight(self.launch[0], self.launch[1], v, self.angle, self.env)
        self.done = False
        self.made = False
        self.wait = 0.0

    def update(self, dt):
        if self.done:
            self.wait += dt
            if self.wait > 1.2:
                self.index += 1
                self.start()
            return
        steps = max(1, int(dt / C.PHYSICS_STEP))
        for _ in range(steps):
            b = self.ball
            b.update(C.PHYSICS_STEP)
            res, _xc = self.hoop.check_scoring(b.prev_x, b.prev_y, b.x, b.y, b.radius)
            if res == 'made':
                self.made = True
            if b.y - b.radius <= 0 or b.x > 12.5:
                self.done = True
                break

    def draw(self, s, renderer):
        f = renderer.fonts
        pygame.draw.rect(s, (30, 40, 70), self.rect, border_radius=10)
        pygame.draw.rect(s, C.PANEL_EDGE, self.rect, 2, border_radius=10)
        pygame.draw.rect(s, C.FLOOR, pygame.Rect(self.rect.x + 2, self.ground_y, self.rect.width - 4, self.rect.bottom - self.ground_y - 2))
        pygame.draw.line(s, C.FLOOR_LINE, (self.rect.x + 2, self.ground_y), (self.rect.right - 2, self.ground_y), 2)
        renderer.draw_preview(s, self.pred, "full", self.w2s, self.scale, clip=self.rect, labels=False)
        renderer.draw_hoop(s, self.hoop, self.w2s, self.scale)
        renderer.draw_launcher(s, self.launch, self.angle, self.w2s)
        b = self.ball
        renderer.draw_ball(s, b.x, b.y, b.spin, self.w2s, 0.3, self.scale)
        renderer.draw_velocity_vectors(s, b.x, b.y, b.vx, b.vy, self.w2s, self.scale, labels=True)
        # gravity arrow
        gx, gy = self.w2s(b.x, b.y)
        draw_arrow(s, (gx + 26, gy - 10), (gx + 26, gy + 26), (255, 255, 255), 2, 8)
        draw_text(s, "g", (gx + 32, gy + 4), f['small'], (255, 255, 255), "midleft")
        label = f"angle {self.angle}{C.DEG}   velocity {self.velocity:.1f} m/s"
        draw_text(s, label, (self.rect.x + 10, self.rect.y + 8), f['small'], C.GOLD)
        if self.made and self.done:
            draw_text(s, "SWISH!", (self.hoop.x * self.scale + self.rect.x, self.rect.y + 30), f['h3'], C.ACCENT2, "midtop")
