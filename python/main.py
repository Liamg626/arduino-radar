"""Arduino sonar display.

    python main.py --port COM3        # real hardware
    python main.py --simulate         # fake sweeping sensor
    python main.py --simulate --fixed # fake fixed sensor (phase 1)
"""

import argparse
import sys

import pygame
from serial.tools import list_ports

from display import RadarDisplay
from source import SerialSource, SimulatedSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submarine-style sonar display for the Arduino radar.")
    parser.add_argument("--port", help="serial port the Uno is on, e.g. COM3")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--simulate", action="store_true", help="use fake data instead of the Arduino")
    parser.add_argument("--fixed", action="store_true", help="with --simulate: fixed sensor, no sweep")
    parser.add_argument("--range", type=int, default=200, dest="max_range", help="display range in cm")
    parser.add_argument("--persist", type=float, default=5.0, help="seconds a blip takes to fade")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.simulate:
        source = SimulatedSource(fixed=args.fixed)
    elif args.port:
        source = SerialSource(args.port, args.baud)
    else:
        ports = [p.device + " - " + p.description for p in list_ports.comports()]
        print("Pass --port <port> or --simulate. Available ports:")
        print("\n".join("  " + p for p in ports) or "  (none found)")
        sys.exit(1)

    pygame.init()
    pygame.display.set_caption("SONAR")
    screen = pygame.display.set_mode((1000, 640))
    clock = pygame.time.Clock()
    radar = RadarDisplay(max_range_cm=args.max_range, persist_s=args.persist)

    source.start()
    try:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False

            for reading in source.poll():
                radar.update(reading)

            radar.draw(screen, source.name, source.error)
            pygame.display.flip()
            clock.tick(60)
    finally:
        source.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
