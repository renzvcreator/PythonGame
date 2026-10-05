"""ui.py - Sliders, buttons and text helpers built on pygame."""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

import pygame

from . import config as C


# --------------------------------------------------------------------------- #
# Text helpers                                                                 #
# --------------------------------------------------------------------------- #
def draw_text(surface, text: str, pos, font, color=C.TEXT, anchor: str = "topleft", shadow=None):
    """Render text with an anchor ('topleft', 'center', 'midtop', 'topright', ...). Returns the rect."""
    if shadow is not None:
        img_s = font.render(text, True, shadow)
        rect_s = img_s.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)})
        surface.blit(img_s, rect_s)
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surface.blit(img, rect)
    return rect


def wrap_text(text: str, font, max_width: int) -> List[str]:
    """Greedy word wrap."""
    words = text.split(" ")
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip()
        if font.size(trial)[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def draw_wrapped(surface, text: str, pos, font, color, max_width: int, line_gap: int = 2) -> int:
    """Draw wrapped text; returns the y just below the last line."""
    x, y = pos
    for line in wrap_text(text, font, max_width):
        draw_text(surface, line, (x, y), font, color)
        y += font.get_linesize() + line_gap
    return y


def draw_arrow(surface, start, end, color, width: int = 3, head: int = 10):
    """Straight arrow from start to end with a filled triangular head."""
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    # shorten the shaft so the head tip is exactly at the end
    bx, by = ex - ux * head, ey - uy * head
    pygame.draw.line(surface, color, (sx, sy), (bx, by), width)
    px, py = -uy, ux
    tri = [(ex, ey), (bx + px * head * 0.5, by + py * head * 0.5), (bx - px * head * 0.5, by - py * head * 0.5)]
    pygame.draw.polygon(surface, color, tri)


def draw_box(surface, rect, fill, edge=None, radius: int = 10, edge_width: int = 2):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if edge is not None:
        pygame.draw.rect(surface, edge, rect, edge_width, border_radius=radius)


# --------------------------------------------------------------------------- #
# Widgets                                                                      #
# --------------------------------------------------------------------------- #
class Button:
    def __init__(self, name: str, rect, text: str, color=C.BTN, hover=C.BTN_HOVER,
                 hotkey: str = "", text_color=C.WHITE):
        self.name = name
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover
        self.hotkey = hotkey
        self.text_color = text_color
        self.enabled = True

    def handle_event(self, event) -> bool:
        """Returns True when the button is clicked."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def draw(self, surface, font, small_font=None):
        hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        color = C.BTN_DISABLED if not self.enabled else (self.hover_color if hovered else self.color)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2, border_radius=8)
        tc = self.text_color if self.enabled else C.TEXT_DIM
        if self.hotkey and small_font is not None:
            draw_text(surface, self.text, (self.rect.centerx, self.rect.centery - 6), font, tc, "center")
            draw_text(surface, self.hotkey, (self.rect.centerx, self.rect.bottom - 10), small_font, tc, "center")
        else:
            draw_text(surface, self.text, self.rect.center, font, tc, "center")


class Slider:
    """Horizontal slider with a label on the left and a value readout on the right."""

    def __init__(self, name: str, track_rect, label: str, vmin: float, vmax: float, step: float,
                 value: float, fmt: Callable[[float], str]):
        self.name = name
        self.track = pygame.Rect(track_rect)
        self.label = label
        self.vmin, self.vmax, self.step = vmin, vmax, step
        self.value = value
        self.fmt = fmt
        self.dragging = False
        self.enabled = True
        self.hit = self.track.inflate(16, 24)

    def _snap(self, v: float) -> float:
        v = min(self.vmax, max(self.vmin, v))
        steps = round((v - self.vmin) / self.step)
        v = self.vmin + steps * self.step
        return round(min(self.vmax, max(self.vmin, v)), 6)

    def set_value(self, v: float) -> bool:
        new = self._snap(v)
        changed = new != self.value
        self.value = new
        return changed

    def nudge(self, steps: int) -> bool:
        return self.set_value(self.value + steps * self.step)

    def _value_from_x(self, x: float) -> float:
        frac = (x - self.track.left) / max(1, self.track.width)
        return self.vmin + frac * (self.vmax - self.vmin)

    def handle_event(self, event) -> bool:
        """Returns True when the value changed."""
        if not self.enabled:
            self.dragging = False
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hit.collidepoint(event.pos):
            self.dragging = True
            return self.set_value(self._value_from_x(event.pos[0]))
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            return self.set_value(self._value_from_x(event.pos[0]))
        if event.type == pygame.MOUSEWHEEL and self.hit.collidepoint(pygame.mouse.get_pos()):
            return self.nudge(event.y)
        return False

    def knob_x(self) -> int:
        frac = (self.value - self.vmin) / (self.vmax - self.vmin)
        return int(self.track.left + frac * self.track.width)

    def draw(self, surface, font, value_font):
        label_color = C.TEXT if self.enabled else C.TEXT_DIM
        draw_text(surface, self.label, (self.track.left - 12, self.track.centery), font, label_color, "midright")
        pygame.draw.rect(surface, C.SLIDER_TRACK, self.track, border_radius=6)
        kx = self.knob_x()
        fill = pygame.Rect(self.track.left, self.track.top, kx - self.track.left, self.track.height)
        pygame.draw.rect(surface, C.SLIDER_FILL if self.enabled else C.BTN_GREY, fill, border_radius=6)
        pygame.draw.circle(surface, C.SLIDER_KNOB if self.enabled else C.TEXT_DIM, (kx, self.track.centery), 11)
        pygame.draw.circle(surface, (0, 0, 0), (kx, self.track.centery), 11, 2)
        draw_text(surface, self.fmt(self.value), (self.track.right + 14, self.track.centery), value_font,
                  C.GOLD if self.enabled else C.TEXT_DIM, "midleft")
