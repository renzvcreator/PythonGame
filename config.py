"""
config.py - Constants, colours and screen layout for Physics Hoops.

World coordinates are in metres with the ground at y = 0 and x increasing to
the right.  Screen coordinates are pixels.  world_to_screen() converts.
"""
import pygame

TITLE = "Physics Hoops: A Projectile Motion Challenge"
WIDTH, HEIGHT = 1280, 720
FPS = 60
PHYSICS_STEP = 1.0 / 120.0        # fixed simulation step (seconds)

# ----- Layout (pixels) ------------------------------------------------------
HEADER_RECT = pygame.Rect(0, 0, WIDTH, 48)
GAME_RECT = pygame.Rect(0, 48, 890, 482)
CONTROL_RECT = pygame.Rect(0, 530, 890, 190)
PANEL_RECT = pygame.Rect(890, 48, 390, 672)

# ----- World scale -----------------------------------------------------------
PX_PER_M = 28.0                                   # pixels per metre
GROUND_SCREEN_Y = 500                             # screen y of the ground line
WORLD_WIDTH_M = GAME_RECT.width / PX_PER_M        # ~31.8 m visible
WORLD_TOP_M = (GROUND_SCREEN_Y - GAME_RECT.top) / PX_PER_M

# ----- Game objects (metres) --------------------------------------------------
BALL_RADIUS_M = 0.40          # exaggerated so the ball is clearly visible
HOOP_WIDTH_M = 1.30           # inner rim width (forgiving target)
BACKBOARD_RESTITUTION = 0.60  # fraction of horizontal speed kept after a backboard bounce
DEFAULT_LAUNCH = (1.5, 2.0)   # ball release point (x, y) in metres

# ----- Controls ---------------------------------------------------------------
ANGLE_MIN, ANGLE_MAX, ANGLE_STEP = 20, 70, 1
VEL_MIN, VEL_MAX, VEL_STEP = 5.0, 30.0, 0.1
DEFAULT_ANGLE = 45
DEFAULT_VELOCITY = 12.0

# ----- Text symbols -----------------------------------------------------------
DEG = "°"
SQ = "²"
ARROW_R = "→"
ARROW_L = "←"
ARROW_UP = "↑"
ARROW_DN = "↓"
THETA = "θ"

# ----- Colours -----------------------------------------------------------------
SKY_TOP = (24, 32, 64)
SKY_BOTTOM = (70, 110, 170)
FLOOR = (196, 134, 78)
FLOOR_DARK = (160, 104, 58)
FLOOR_LINE = (240, 230, 210)
WALL = (46, 56, 88)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEXT = (235, 238, 245)
TEXT_DIM = (160, 170, 190)
ORANGE = (245, 130, 32)
BALL_ORANGE = (236, 108, 33)
BALL_SEAM = (70, 30, 10)
RIM = (240, 90, 40)
NET = (235, 235, 235)
BACKBOARD = (236, 240, 245)
BACKBOARD_LINE = (200, 40, 40)
POLE = (120, 125, 140)
OBSTACLE = (120, 60, 50)
OBSTACLE_EDGE = (80, 36, 30)

PANEL_BG = (28, 32, 48)
PANEL_BOX = (38, 44, 66)
PANEL_EDGE = (70, 80, 110)
CONTROL_BG = (34, 38, 56)
HEADER_BG = (20, 22, 36)

ACCENT = (80, 200, 255)       # blue - horizontal
ACCENT2 = (120, 230, 120)     # green - vertical
ACCENT3 = (255, 110, 110)     # red - resultant / warnings
GOLD = (255, 205, 70)
PREVIEW = (255, 255, 255)
TRAIL = (255, 190, 80)

BTN = (60, 120, 220)
BTN_HOVER = (90, 150, 245)
BTN_GREEN = (50, 170, 90)
BTN_GREEN_HOVER = (70, 200, 110)
BTN_GREY = (90, 95, 110)
BTN_GREY_HOVER = (115, 120, 135)
BTN_ORANGE = (230, 120, 40)
BTN_ORANGE_HOVER = (250, 145, 60)
BTN_DISABLED = (60, 62, 72)
SLIDER_TRACK = (60, 66, 90)
SLIDER_FILL = (80, 200, 255)
SLIDER_KNOB = (255, 255, 255)

SAVE_FILE = "physics_hoops_save.json"


def world_to_screen(x: float, y: float):
    """Convert world metres to screen pixels inside the game area."""
    return (GAME_RECT.x + x * PX_PER_M, GROUND_SCREEN_Y - y * PX_PER_M)


def screen_to_world(sx: float, sy: float):
    """Inverse of world_to_screen (used for hover readouts)."""
    return ((sx - GAME_RECT.x) / PX_PER_M, (GROUND_SCREEN_Y - sy) / PX_PER_M)


def m_to_px(m: float) -> float:
    return m * PX_PER_M
