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

HOT = (150, 255, 175)  # colour of a fresh echo before it cools to GREEN

TRAIL_DEGREES = 25
PANEL_HEIGHT = 80
MARGIN = 40

ECHO_WIDTH_DEG = 5     # wider than the 2 degree sweep step so neighbouring echoes merge
ECHO_DEPTH_PX = 9      # radial thickness of each echo
TIGHT_GLOW = (2, 2)    # downscale factors for blurring: tight halo hugging each echo
WIDE_GLOW = (4, 4)     # ...and a wide soft bloom that merges nearby contacts


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

    def _polar(self, angle: float, r_px: float) -> tuple[float, float]:
        rad = math.radians(angle)
        return self.cx + r_px * math.cos(rad), self.cy - r_px * math.sin(rad)

    def _to_xy(self, angle: float, distance_cm: float) -> tuple[float, float]:
        return self._polar(angle, distance_cm / self.max_range * self.radius)

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

    def _echo_polygon(self, angle: float, distance_cm: float) -> list[tuple[float, float]]:
        """Annular sector covering one echo: a short thick arc centred on the reading."""
        r = distance_cm / self.max_range * self.radius
        r_out, r_in = r + ECHO_DEPTH_PX / 2, max(0, r - ECHO_DEPTH_PX / 2)
        steps = 4
        angles = [angle - ECHO_WIDTH_DEG / 2 + ECHO_WIDTH_DEG * i / steps for i in range(steps + 1)]
        outer = [self._polar(a, r_out) for a in angles]
        inner = [self._polar(a, r_in) for a in reversed(angles)]
        return outer + inner

    def _render_echoes(self, now: float) -> pygame.Surface:
        """Echoes on a black layer, meant to be added onto the screen (black adds nothing).
        Oldest first, so fresher, brighter echoes are painted over older ones they overlap."""
        layer = pygame.Surface((self.width, self.height))
        for blip in sorted(self.blips, key=lambda b: b.born):
            life = (now - blip.born) / self.persist
            heat = max(0.0, 1 - life * 4)  # first quarter of its life: HOT -> GREEN
            brightness = (1 - life) ** 1.5
            colour = [int((g + (h - g) * heat) * brightness) for h, g in zip(HOT, GREEN)]
            pygame.draw.polygon(layer, colour, self._echo_polygon(blip.angle, blip.distance_cm))
        return layer

    def _blur(self, surf: pygame.Surface, factors: tuple[int, ...]) -> pygame.Surface:
        w, h = surf.get_size()
        small = surf
        for factor in factors:
            w, h = max(1, w // factor), max(1, h // factor)
            small = pygame.transform.smoothscale(small, (w, h))
        return pygame.transform.smoothscale(small, surf.get_size())

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
        # Additive blending: blurred glow first so nearby echoes bleed together, then the sharp echoes.
        echoes = self._render_echoes(now)
        wide = self._blur(echoes, WIDE_GLOW)
        surf.blit(wide, (0, 0), special_flags=pygame.BLEND_ADD)
        surf.blit(self._blur(echoes, TIGHT_GLOW), (0, 0), special_flags=pygame.BLEND_ADD)
        surf.blit(echoes, (0, 0), special_flags=pygame.BLEND_ADD)

        if self.angle is not None:
            sweep = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._draw_sweep(sweep)
            surf.blit(sweep, (0, 0))
        self._draw_panel(surf, source_name, error)
