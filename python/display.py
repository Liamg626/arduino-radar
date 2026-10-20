"""Submarine-style sonar display drawn with pygame."""

import math
import time
from dataclasses import dataclass

import pygame

from source import Reading

BG = (2, 12, 6)
GREEN = (60, 255, 120)
DIM = (0, 120, 50)
FAINT = (0, 55, 25)
WARN = (255, 170, 40)

TRAIL_DEGREES = 25
PANEL_HEIGHT = 80
MARGIN = 40


@dataclass
class Blip:
    angle: int
    distance_cm: int
    born: float


def bearing(angle: float) -> int:
    """Servo angle (0 right, 90 ahead, 180 left) -> compass-style bearing (000 ahead, 090 right)."""
    return round(90 - angle) % 360


class RadarDisplay:
    def __init__(self, size=(1000, 640), max_range_cm=200, persist_s=5.0, ring_step_cm=50):
        self.width, self.height = size
        self.max_range = max_range_cm
        self.persist = persist_s
        self.ring_step = ring_step_cm

        self.cx = self.width // 2
        self.cy = self.height - PANEL_HEIGHT - 20
        self.radius = min(self.width // 2 - 2 * MARGIN, self.cy - MARGIN)

        self.font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 22, bold=True)

        self.blips: list[Blip] = []
        self.angle: int | None = None
        self.last_distance: int | None = None
        self.direction = 0  # +1 sweeping left, -1 sweeping right, 0 static

        self._background = self._render_background()

    # --- state ---------------------------------------------------------------

    def update(self, reading: Reading):
        if self.angle is not None and reading.angle != self.angle:
            self.direction = 1 if reading.angle > self.angle else -1
        self.angle = reading.angle
        self.last_distance = reading.distance_cm
        if reading.has_echo and reading.distance_cm <= self.max_range:
            self.blips.append(Blip(reading.angle, reading.distance_cm, time.monotonic()))

    def _expire_blips(self, now: float):
        self.blips = [b for b in self.blips if now - b.born < self.persist]

    # --- drawing -------------------------------------------------------------

    def _to_xy(self, angle: float, distance_cm: float) -> tuple[float, float]:
        r = distance_cm / self.max_range * self.radius
        rad = math.radians(angle)
        return self.cx + r * math.cos(rad), self.cy - r * math.sin(rad)

    def _render_background(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height))
        surf.fill(BG)
        centre = (self.cx, self.cy)

        # Range rings with labels along the right-hand baseline.
        for cm in range(self.ring_step, self.max_range + 1, self.ring_step):
            r = cm / self.max_range * self.radius
            rect = pygame.Rect(self.cx - r, self.cy - r, 2 * r, 2 * r)
            colour = DIM if cm == self.max_range else FAINT
            pygame.draw.arc(surf, colour, rect, 0, math.pi, 2 if cm == self.max_range else 1)
            label = self.font.render(f"{cm}", True, DIM)
            surf.blit(label, (self.cx + r - label.get_width() / 2, self.cy + 4))

        # Bearing lines every 30 degrees.
        for angle in range(0, 181, 30):
            end = self._to_xy(angle, self.max_range)
            pygame.draw.line(surf, FAINT, centre, end, 1)
            label = self.font.render(f"{bearing(angle):03d}", True, DIM)
            lx, ly = self._to_xy(angle, self.max_range * 1.07)
            surf.blit(label, (lx - label.get_width() / 2, ly - label.get_height() / 2))

        pygame.draw.line(surf, DIM, (self.cx - self.radius, self.cy), (self.cx + self.radius, self.cy), 2)
        pygame.draw.line(surf, FAINT, (0, self.height - PANEL_HEIGHT), (self.width, self.height - PANEL_HEIGHT), 1)
        return surf

    def _draw_sweep(self, overlay: pygame.Surface):
        centre = (self.cx, self.cy)

        # Fading wedge trailing behind the direction of travel.
        if self.direction:
            for i in range(TRAIL_DEGREES):
                a0 = self.angle - self.direction * i
                a1 = a0 - self.direction
                alpha = int(90 * (1 - i / TRAIL_DEGREES))
                points = [centre, self._to_xy(a0, self.max_range), self._to_xy(a1, self.max_range)]
                pygame.draw.polygon(overlay, (*GREEN, alpha), points)

        pygame.draw.line(overlay, (*GREEN, 230), centre, self._to_xy(self.angle, self.max_range), 3)

    def _draw_blips(self, overlay: pygame.Surface, now: float):
        for blip in self.blips:
            fade = 1 - (now - blip.born) / self.persist
            x, y = self._to_xy(blip.angle, blip.distance_cm)
            pygame.draw.circle(overlay, (*GREEN, int(60 * fade)), (x, y), 11)  # glow
            pygame.draw.circle(overlay, (*GREEN, int(255 * fade)), (x, y), 5)

    def _draw_panel(self, surf: pygame.Surface, source_name: str, error: str | None):
        y = self.height - PANEL_HEIGHT + 14

        if error:
            text, colour = f"SERIAL ERROR: {error}", WARN
        elif self.angle is None:
            text, colour = "WAITING FOR DATA...", WARN
        else:
            if self.last_distance is not None and self.last_distance >= 0:
                rng = f"{self.last_distance:>3d} cm"
            else:
                rng = "NO ECHO"
            text = f"BRG {bearing(self.angle):03d}    RNG {rng:<7}    ECHOES {len(self.blips):>3d}"
            colour = GREEN
        surf.blit(self.big_font.render(text, True, colour), (MARGIN, y))

        info = f"SOURCE {source_name}    RANGE {self.max_range} cm    PERSIST {self.persist:g} s    [Q] quit"
        surf.blit(self.font.render(info, True, DIM), (MARGIN, y + 34))

    def draw(self, surf: pygame.Surface, source_name: str = "", error: str | None = None):
        now = time.monotonic()
        self._expire_blips(now)

        surf.blit(self._background, (0, 0))
        # Separate layers: drawing onto an SRCALPHA surface replaces pixels rather than blending.
        if self.angle is not None:
            sweep = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._draw_sweep(sweep)
            surf.blit(sweep, (0, 0))
        blips = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self._draw_blips(blips, now)
        surf.blit(blips, (0, 0))
        self._draw_panel(surf, source_name, error)
