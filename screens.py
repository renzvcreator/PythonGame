"""screens.py - Full-screen menus: main menu, tutorial / how-to-play, level select, pause, course complete."""
from __future__ import annotations

from typing import List

import pygame

from . import config as C
from .levels import LEVELS, MAIN_COURSE_COUNT
from .ui import draw_box, draw_text, draw_wrapped

DEMO_RECT = pygame.Rect(720, 150, 520, 300)


def _background(s, renderer):
    s.fill(C.PANEL_BG)
    # a faint court strip at the bottom
    pygame.draw.rect(s, C.FLOOR_DARK, pygame.Rect(0, C.HEIGHT - 70, C.WIDTH, 70))
    pygame.draw.line(s, C.FLOOR_LINE, (0, C.HEIGHT - 70), (C.WIDTH, C.HEIGHT - 70), 3)


def draw_menu(s, renderer, game):
    _background(s, renderer)
    f = renderer.fonts
    draw_text(s, "PHYSICS HOOPS", (C.WIDTH // 2, 110), f['huge'], C.ORANGE, "center", shadow=(0, 0, 0))
    draw_text(s, "A Projectile Motion Challenge", (C.WIDTH // 2, 170), f['h2'], C.TEXT, "center")
    draw_text(s, "Use angle, velocity and gravity to put the ball through the hoop.",
              (C.WIDTH // 2, 205), f['body'], C.TEXT_DIM, "center")
    # live demo
    demo_rect = pygame.Rect(40, 300, 360, 250)
    _draw_demo_in(s, renderer, game, demo_rect)
    # leaderboard
    box = pygame.Rect(C.WIDTH - 400, 300, 360, 250)
    draw_box(s, box, C.PANEL_BOX, C.PANEL_EDGE)
    draw_text(s, "LEADERBOARD", (box.x + 16, box.y + 12), f['h3'], C.GOLD)
    sv = game.save
    y = box.y + 46
    rows = [("Highest score", f"{sv.best_total}"),
            ("Best accuracy bonus", f"+{sv.best_accuracy}"),
            ("Levels completed", f"{sum(1 for k, v in sv.completed.items() if v and int(k) <= MAIN_COURSE_COUNT)} / {MAIN_COURSE_COUNT}")]
    fewest = [v for k, v in sv.fewest_attempts.items()]
    rows.append(("Fewest attempts (any level)", f"{min(fewest)}" if fewest else "-"))
    if sv.fastest_completion > 0:
        m, sec = divmod(int(sv.fastest_completion), 60)
        rows.append(("Fastest course completion", f"{m}m {sec:02d}s"))
    for label, value in rows:
        draw_text(s, label, (box.x + 16, y), f['body'], C.TEXT_DIM)
        draw_text(s, value, (box.right - 16, y), f['mono'], C.TEXT, "topright")
        y += 30
    draw_text(s, "ENTER = play    H = how to play    L = level select", (C.WIDTH // 2, C.HEIGHT - 30),
              f['small'], C.TEXT_DIM, "center")


def _draw_demo_in(s, renderer, game, rect):
    demo = game.demo
    demo.rect = pygame.Rect(rect)
    demo.scale = demo.rect.width / 12.0
    demo.ground_y = demo.rect.bottom - 22
    demo.draw(s, renderer)
    draw_text(s, "live simulation: same equations as the game", (rect.centerx, rect.bottom + 6),
              renderer.fonts['tiny'], C.TEXT_DIM, "midtop")


def draw_tutorial(s, renderer, game, background: bool = True):
    if background:
        _background(s, renderer)
    f = renderer.fonts
    draw_text(s, "HOW TO PLAY", (C.WIDTH // 2, 50), f['h1'], C.ORANGE, "center", shadow=(0, 0, 0))
    draw_text(s, "Make the basketball reach the hoop using projectile-motion principles.",
              (C.WIDTH // 2, 95), f['body'], C.TEXT, "center")
    steps = [
        ("1. Choose an Angle", "The angle controls how steep the arc is. A higher angle sends the ball "
                               "higher (and takes longer); a lower angle gives a flatter path."),
        ("2. Choose a Velocity", "Velocity is how fast the ball leaves the launcher. More velocity means the "
                                 "ball travels farther and higher."),
        ("3. Press SHOOT", "The game splits the velocity into Vx = V0 cos(angle) and Vy = V0 sin(angle) and "
                           "computes the position every frame: x = x0 + Vx t,  y = y0 + Vy t - 1/2 g t²."),
        ("4. Watch the Trajectory", "The ball keeps moving forward at a constant Vx while gravity "
                                    "(g = 9.81 m/s²) steadily pulls Vy downward. The two motions happen at the same time."),
        ("5. Score", "The ball must drop THROUGH the rim from above. Read the result to learn why a shot "
                     "missed, then adjust the angle or velocity."),
    ]
    x, y = 60, 140
    width = 600
    for title, body in steps:
        draw_text(s, title, (x, y), f['h3'], C.GOLD)
        y = draw_wrapped(s, body, (x, y + 24), f['body'], C.TEXT, width) + 10
    _draw_demo_in(s, renderer, game, DEMO_RECT)
    # legend
    lx, ly = DEMO_RECT.x, DEMO_RECT.bottom + 34
    legend = [(C.ACCENT, "Vx - horizontal velocity (constant)"), (C.ACCENT2, "Vy - vertical velocity (changes by g every second)"),
              (C.ACCENT3, "resultant velocity"), ((255, 255, 255), "dotted path = predicted trajectory")]
    for col, text in legend:
        pygame.draw.rect(s, col, pygame.Rect(lx, ly + 4, 14, 14), border_radius=3)
        draw_text(s, text, (lx + 22, ly), f['small'], C.TEXT)
        ly += 24
    draw_text(s, "Controls: sliders or arrow keys (Shift = bigger steps), SPACE to shoot, R reset, P pause, "
                 "V velocity arrows, S slow motion, H this screen.",
              (C.WIDTH // 2, 626), f['small'], C.TEXT_DIM, "center")


def level_card_rects(count: int) -> List[pygame.Rect]:
    cols = 4
    w, h, gap = 270, 170, 20
    x0 = (C.WIDTH - (cols * w + (cols - 1) * gap)) // 2
    y0 = 150
    rects = []
    for i in range(count):
        r, c = divmod(i, cols)
        rects.append(pygame.Rect(x0 + c * (w + gap), y0 + r * (h + gap), w, h))
    return rects


def draw_level_select(s, renderer, game):
    _background(s, renderer)
    f = renderer.fonts
    draw_text(s, "LEVEL SELECT", (C.WIDTH // 2, 60), f['h1'], C.ORANGE, "center", shadow=(0, 0, 0))
    draw_text(s, "Each level introduces a new idea about projectile motion. Press U to unlock everything (teacher mode).",
              (C.WIDTH // 2, 105), f['body'], C.TEXT_DIM, "center")
    mouse = pygame.mouse.get_pos()
    for i, (rect, lv) in enumerate(zip(game.level_cards, LEVELS)):
        unlocked = i < game.save.unlocked
        hovered = unlocked and rect.collidepoint(mouse)
        fill = C.PANEL_BOX if unlocked else (30, 32, 42)
        if hovered:
            fill = (50, 60, 90)
        edge = C.GOLD if lv.bonus and unlocked else (C.PANEL_EDGE if unlocked else (50, 52, 60))
        draw_box(s, rect, fill, edge)
        col = C.TEXT if unlocked else C.TEXT_DIM
        draw_text(s, f"LEVEL {lv.number}" + ("  (BONUS)" if lv.bonus else ""), (rect.x + 14, rect.y + 12), f['small'], C.GOLD if unlocked else C.TEXT_DIM)
        draw_text(s, lv.name, (rect.x + 14, rect.y + 32), f['h3'], col)
        y = draw_wrapped(s, lv.subtitle, (rect.x + 14, rect.y + 58), f['small'], col, rect.width - 28)
        draw_wrapped(s, "Teaches: " + ", ".join(lv.teaches), (rect.x + 14, y + 2), f['tiny'],
                     C.ACCENT if unlocked else C.TEXT_DIM, rect.width - 28)
        key = str(lv.number)
        if unlocked:
            best = game.save.best_level_scores.get(key)
            done = game.save.completed.get(key, False)
            status = f"Best: {best}   Fewest shots: {game.save.fewest_attempts.get(key, '-')}" if done else "Not completed yet"
            draw_text(s, status, (rect.x + 14, rect.bottom - 24), f['tiny'], C.ACCENT2 if done else C.TEXT_DIM)
        else:
            draw_text(s, "LOCKED - complete the previous level", (rect.x + 14, rect.bottom - 24), f['tiny'], C.ACCENT3)
    draw_text(s, "Click a level or press its number key.", (C.WIDTH // 2, 580), f['small'], C.TEXT_DIM, "center")


def draw_pause(s, renderer, game):
    f = renderer.fonts
    draw_text(s, "PAUSED", (C.GAME_RECT.centerx, 150), f['h1'], C.GOLD, "center", shadow=(0, 0, 0))
    draw_text(s, "The simulation is frozen. Study the velocity arrows and the information panel.",
              (C.GAME_RECT.centerx, 200), f['body'], C.TEXT, "center")


def draw_game_complete(s, renderer, game):
    _background(s, renderer)
    f = renderer.fonts
    draw_text(s, "COURSE COMPLETE!", (C.WIDTH // 2, 90), f['huge'], C.GOLD, "center", shadow=(0, 0, 0))
    draw_text(s, "You used projectile-motion principles to beat every challenge.", (C.WIDTH // 2, 150), f['h2'], C.TEXT, "center")
    box = pygame.Rect(C.WIDTH // 2 - 300, 200, 600, 250)
    draw_box(s, box, C.PANEL_BOX, C.PANEL_EDGE)
    y = box.y + 20
    rows = [("Total score", f"{game.total_score}"),
            ("Shots taken", f"{game.shots_total}"),
            ("Shots made", f"{game.shots_made}"),
            ("Shooting accuracy", f"{(100 * game.shots_made / game.shots_total) if game.shots_total else 0:.0f}%")]
    if game.course_time:
        m, sec = divmod(int(game.course_time), 60)
        rows.append(("Time to complete the course", f"{m}m {sec:02d}s"))
    for label, value in rows:
        draw_text(s, label, (box.x + 24, y), f['h3'], C.TEXT_DIM)
        draw_text(s, value, (box.right - 24, y), f['mono_b'], C.TEXT, "topright")
        y += 40
    lessons = ["Angle changes the SHAPE of the arc.", "Velocity changes how FAR and how HIGH the ball goes.",
               "Gravity pulls the ball down the whole time: Vy = V0 sin(angle) - g t.",
               "Horizontal and vertical motion happen at the same time, independently."]
    y = 470
    for text in lessons:
        draw_text(s, "- " + text, (C.WIDTH // 2, y), f['body'], C.ACCENT2, "center")
        y += 26
