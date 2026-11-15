"""
Flappy Bird - Python
A complete Flappy Bird clone using Pygame.
Everything is drawn with code (no image or sound files needed).

Controls:
    SPACE / UP ARROW / Mouse Click = Flap
    P = Pause / Resume
    R = Restart after Game Over
"""

import math
import os
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 400, 600
FPS = 60
TITLE = "Flappy Bird - Python"

GROUND_HEIGHT = 80
GROUND_Y = HEIGHT - GROUND_HEIGHT        # y where the ground begins

# Bird
BIRD_X = 100
BIRD_RADIUS = 15
GRAVITY = 0.5
FLAP_STRENGTH = -8.0
MAX_FALL_SPEED = 12

# Pipes
PIPE_WIDTH = 60
PIPE_GAP = 150
PIPE_SPAWN_MS = 1500                     # spawn a pipe every 1.5 seconds
PIPE_BASE_SPEED = 3
PIPE_SPEED_STEP = 0.3                    # extra speed every 5 points
PIPE_MAX_SPEED = 7
CAP_HEIGHT = 24                          # the wider "lip" on each pipe
CAP_OVERHANG = 4

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_TOP = (70, 170, 235)
SKY_BOTTOM = (180, 225, 250)
YELLOW = (255, 220, 40)
ORANGE = (255, 140, 0)
PIPE_GREEN = (80, 200, 60)
PIPE_DARK = (30, 100, 25)
GROUND_BROWN = (150, 100, 50)
GROUND_DARK = (120, 78, 38)
GRASS_GREEN = (100, 190, 50)

# Game states
STATE_START, STATE_PLAYING, STATE_PAUSED, STATE_OVER = range(4)

# Best score file (stored next to main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BEST_SCORE_FILE = os.path.join(BASE_DIR, "best_score.txt")


# ----------------------------------------------------------------------------
# Best score persistence
# ----------------------------------------------------------------------------
def load_best_score():
    """Read the best score from best_score.txt (0 if missing/invalid)."""
    try:
        with open(BEST_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_best_score(score):
    """Write the best score to best_score.txt."""
    try:
        with open(BEST_SCORE_FILE, "w") as f:
            f.write(str(score))
    except OSError:
        pass  # Not being able to save should never crash the game


# ----------------------------------------------------------------------------
# Background helpers
# ----------------------------------------------------------------------------
def make_sky_surface():
    """Pre-render the sky blue vertical gradient once."""
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(SKY_TOP[i] + (SKY_BOTTOM[i] - SKY_TOP[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (WIDTH, y))
    return surf


def make_clouds():
    """Create a handful of clouds with random position, size and speed."""
    return [
        {
            "x": random.randint(0, WIDTH),
            "y": random.randint(30, 300),
            "scale": random.uniform(0.7, 1.3),
            "speed": random.uniform(0.3, 0.8),
        }
        for _ in range(5)
    ]


def update_clouds(clouds):
    """Move clouds left slowly; wrap around when they leave the screen."""
    for c in clouds:
        c["x"] -= c["speed"]
        if c["x"] < -100:
            c["x"] = WIDTH + random.randint(20, 100)
            c["y"] = random.randint(30, 300)


def draw_clouds(surface, clouds):
    """Draw white clouds built from overlapping circles."""
    for c in clouds:
        x, y, s = c["x"], c["y"], c["scale"]
        pygame.draw.circle(surface, WHITE, (int(x), int(y)), int(20 * s))
        pygame.draw.circle(surface, WHITE, (int(x + 22 * s), int(y - 10 * s)), int(25 * s))
        pygame.draw.circle(surface, WHITE, (int(x + 48 * s), int(y)), int(20 * s))
        pygame.draw.rect(surface, WHITE,
                         (int(x), int(y), int(48 * s), int(20 * s)),
                         border_radius=int(10 * s))


def draw_ground(surface, offset):
    """Draw brown ground with a green grass strip; offset scrolls the stripes."""
    pygame.draw.rect(surface, GROUND_BROWN, (0, GROUND_Y, WIDTH, GROUND_HEIGHT))
    # Scrolling dirt stripes for a sense of motion
    for x in range(-40, WIDTH + 40, 40):
        sx = x - (offset % 40)
        pygame.draw.polygon(surface, GROUND_DARK, [
            (sx, GROUND_Y + 20), (sx + 20, GROUND_Y + 20),
            (sx + 10, GROUND_Y + GROUND_HEIGHT), (sx - 10, GROUND_Y + GROUND_HEIGHT),
        ])
    # Grass on top
    pygame.draw.rect(surface, GRASS_GREEN, (0, GROUND_Y, WIDTH, 18))
    pygame.draw.line(surface, PIPE_DARK, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)


# ----------------------------------------------------------------------------
# Bird
# ----------------------------------------------------------------------------
def draw_bird(surface, x, y, velocity):
    """Draw the bird (yellow body, orange beak, eye) tilted by its velocity."""
    size = BIRD_RADIUS * 4
    bird_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2

    # Body
    pygame.draw.circle(bird_surf, YELLOW, (c, c), BIRD_RADIUS)
    pygame.draw.circle(bird_surf, ORANGE, (c, c), BIRD_RADIUS, 2)
    # Wing
    pygame.draw.ellipse(bird_surf, (240, 190, 20), (c - 12, c - 2, 14, 9))
    # Beak (orange triangle)
    pygame.draw.polygon(bird_surf, ORANGE, [
        (c + BIRD_RADIUS - 2, c - 3),
        (c + BIRD_RADIUS + 10, c + 2),
        (c + BIRD_RADIUS - 2, c + 7),
    ])
    # Eye (white with black pupil)
    pygame.draw.circle(bird_surf, WHITE, (c + 6, c - 5), 5)
    pygame.draw.circle(bird_surf, BLACK, (c + 8, c - 5), 2)

    # Tilt up when rising, nose-dive when falling
    angle = max(-70, min(-velocity * 4, 30))
    rotated = pygame.transform.rotate(bird_surf, angle)
    surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))))


# ----------------------------------------------------------------------------
# Pipes
# ----------------------------------------------------------------------------
def new_pipe():
    """Create a pipe dict with a random gap position."""
    gap_top = random.randint(80, GROUND_Y - 80 - PIPE_GAP)
    return {"x": WIDTH + 10, "gap_top": gap_top, "passed": False}


def pipe_rects(pipe):
    """Return (top_rect, bottom_rect) of a pipe's bodies for collision."""
    top = pygame.Rect(pipe["x"], 0, PIPE_WIDTH, pipe["gap_top"])
    bottom_y = pipe["gap_top"] + PIPE_GAP
    bottom = pygame.Rect(pipe["x"], bottom_y, PIPE_WIDTH, GROUND_Y - bottom_y)
    return top, bottom


def _draw_pipe_section(surface, rect, cap_at_bottom):
    """Draw one pipe half: green body, dark green border, wider cap."""
    # Body
    pygame.draw.rect(surface, PIPE_GREEN, rect)
    pygame.draw.rect(surface, PIPE_DARK, rect, 3)
    # Highlight stripe
    pygame.draw.rect(surface, (130, 230, 100), (rect.x + 8, rect.y, 6, rect.height))
    # Cap
    cap_y = rect.bottom - CAP_HEIGHT if cap_at_bottom else rect.top
    cap = pygame.Rect(rect.x - CAP_OVERHANG, cap_y, rect.width + CAP_OVERHANG * 2, CAP_HEIGHT)
    pygame.draw.rect(surface, PIPE_GREEN, cap)
    pygame.draw.rect(surface, PIPE_DARK, cap, 3)
    pygame.draw.rect(surface, (130, 230, 100), (cap.x + 8, cap.y + 3, 6, cap.height - 6))


def draw_pipes(surface, pipes):
    """Draw every pipe (top and bottom halves)."""
    for pipe in pipes:
        top, bottom = pipe_rects(pipe)
        if top.height > 0:
            _draw_pipe_section(surface, top, cap_at_bottom=True)
        if bottom.height > 0:
            _draw_pipe_section(surface, bottom, cap_at_bottom=False)


# ----------------------------------------------------------------------------
# Collision
# ----------------------------------------------------------------------------
def circle_hits_rect(cx, cy, radius, rect):
    """Circle vs. rectangle collision test."""
    nearest_x = max(rect.left, min(cx, rect.right))
    nearest_y = max(rect.top, min(cy, rect.bottom))
    dx, dy = cx - nearest_x, cy - nearest_y
    return dx * dx + dy * dy < radius * radius


def check_collision(bird_y, pipes):
    """Return True if the bird hits the ground, the top, or any pipe."""
    if bird_y + BIRD_RADIUS >= GROUND_Y:   # ground
        return True
    if bird_y - BIRD_RADIUS <= 0:          # top of screen
        return True
    for pipe in pipes:
        top, bottom = pipe_rects(pipe)
        if (circle_hits_rect(BIRD_X, bird_y, BIRD_RADIUS - 1, top) or
                circle_hits_rect(BIRD_X, bird_y, BIRD_RADIUS - 1, bottom)):
            return True
    return False


# ----------------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------------
def draw_text_outline(surface, text, font, center, color=WHITE, outline=BLACK, width=2):
    """Draw text with an outline, centered at `center`."""
    base = font.render(text, True, color)
    edge = font.render(text, True, outline)
    rect = base.get_rect(center=center)
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                surface.blit(edge, rect.move(dx, dy))
    surface.blit(base, rect)


def show_score(surface, score, font):
    """Show the current score at the top center (big, white, bold, outlined)."""
    draw_text_outline(surface, str(score), font, (WIDTH // 2, 50), width=3)


# ----------------------------------------------------------------------------
# Screens
# ----------------------------------------------------------------------------
def draw_start_screen(surface, fonts, best):
    draw_text_outline(surface, "FLAPPY BIRD", fonts["title"], (WIDTH // 2, 150), YELLOW, width=3)
    draw_text_outline(surface, "Press SPACE to Start", fonts["medium"], (WIDTH // 2, 400))
    draw_text_outline(surface, f"Best Score: {best}", fonts["medium"], (WIDTH // 2, 445))
    draw_text_outline(surface, "P = Pause", fonts["small"], (WIDTH // 2, 490))


def draw_game_over_screen(surface, fonts, score, best):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 110))
    surface.blit(overlay, (0, 0))
    draw_text_outline(surface, "GAME OVER", fonts["title"], (WIDTH // 2, 180), (255, 80, 60), width=3)
    draw_text_outline(surface, f"Score: {score}", fonts["medium"], (WIDTH // 2, 270))
    draw_text_outline(surface, f"Best Score: {best}", fonts["medium"], (WIDTH // 2, 315))
    draw_text_outline(surface, "Press R to Restart", fonts["medium"], (WIDTH // 2, 400))


def draw_pause_screen(surface, fonts):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 90))
    surface.blit(overlay, (0, 0))
    draw_text_outline(surface, "PAUSED", fonts["title"], (WIDTH // 2, 260), width=3)
    draw_text_outline(surface, "Press P to Resume", fonts["small"], (WIDTH // 2, 320))


# ----------------------------------------------------------------------------
# Main game
# ----------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    fonts = {
        "score": pygame.font.SysFont("arial", 64, bold=True),
        "title": pygame.font.SysFont("arial", 48, bold=True),
        "medium": pygame.font.SysFont("arial", 28, bold=True),
        "small": pygame.font.SysFont("arial", 20, bold=True),
    }

    sky = make_sky_surface()
    clouds = make_clouds()
    best_score = load_best_score()

    def reset():
        """Return fresh values for a new round."""
        return {"y": HEIGHT // 2, "vel": 0.0, "pipes": [], "score": 0,
                "spawn_timer": 0, "speed": PIPE_BASE_SPEED}

    g = reset()
    state = STATE_START
    ground_offset = 0.0

    while True:
        dt = clock.tick(FPS)  # milliseconds since last frame

        # ---------------- Events ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            flap = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    flap = True
                elif event.key == pygame.K_p and state in (STATE_PLAYING, STATE_PAUSED):
                    state = STATE_PAUSED if state == STATE_PLAYING else STATE_PLAYING
                elif event.key == pygame.K_r and state == STATE_OVER:
                    g = reset()
                    state = STATE_PLAYING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                flap = True

            if flap:
                if state == STATE_START:
                    state = STATE_PLAYING
                    g["vel"] = FLAP_STRENGTH
                elif state == STATE_PLAYING:
                    g["vel"] = FLAP_STRENGTH

        # ---------------- Update ----------------
        if state != STATE_PAUSED:
            update_clouds(clouds)

        if state == STATE_START:
            # Bird gently bobs up and down
            g["y"] = HEIGHT // 2 + math.sin(pygame.time.get_ticks() / 250) * 10
            g["vel"] = 0
            ground_offset += PIPE_BASE_SPEED

        elif state == STATE_PLAYING:
            # Bird physics
            g["vel"] = min(g["vel"] + GRAVITY, MAX_FALL_SPEED)
            g["y"] += g["vel"]
            ground_offset += g["speed"]

            # Spawn pipes every 1.5 seconds
            g["spawn_timer"] += dt
            if g["spawn_timer"] >= PIPE_SPAWN_MS or not g["pipes"]:
                g["spawn_timer"] = 0
                g["pipes"].append(new_pipe())

            # Move pipes, score, and remove off-screen ones
            for pipe in g["pipes"]:
                pipe["x"] -= g["speed"]
                if not pipe["passed"] and pipe["x"] + PIPE_WIDTH < BIRD_X - BIRD_RADIUS:
                    pipe["passed"] = True
                    g["score"] += 1
                    # Speed up slightly every 5 points
                    g["speed"] = min(PIPE_BASE_SPEED + (g["score"] // 5) * PIPE_SPEED_STEP,
                                     PIPE_MAX_SPEED)
            g["pipes"] = [p for p in g["pipes"] if p["x"] + PIPE_WIDTH + CAP_OVERHANG > 0]

            # Collision -> game over
            if check_collision(g["y"], g["pipes"]):
                state = STATE_OVER
                g["y"] = min(g["y"], GROUND_Y - BIRD_RADIUS)
                if g["score"] > best_score:
                    best_score = g["score"]
                    save_best_score(best_score)

        # ---------------- Draw ----------------
        screen.blit(sky, (0, 0))
        draw_clouds(screen, clouds)
        draw_pipes(screen, g["pipes"])
        draw_ground(screen, ground_offset)
        draw_bird(screen, BIRD_X, g["y"], g["vel"])

        if state in (STATE_PLAYING, STATE_PAUSED, STATE_OVER):
            show_score(screen, g["score"], fonts["score"])

        if state == STATE_START:
            draw_start_screen(screen, fonts, best_score)
        elif state == STATE_PAUSED:
            draw_pause_screen(screen, fonts)
        elif state == STATE_OVER:
            draw_game_over_screen(screen, fonts, g["score"], best_score)

        pygame.display.flip()


if __name__ == "__main__":
    main()
