"""Reading sources: the real Arduino over serial, or a simulator for working without hardware.

Both run in a background thread and expose the same interface: start(), poll(), stop(), error.
"""

import math
import queue
import random
import threading
import time
from dataclasses import dataclass

import serial


@dataclass(frozen=True)
class Reading:
    angle: int        # servo angle in degrees, 0 = right, 90 = ahead, 180 = left
    distance_cm: int  # -1 = no echo

    @property
    def has_echo(self) -> bool:
        return self.distance_cm >= 0


def parse_line(line: str) -> Reading | None:
    """Parse an "<angle>,<distance_cm>" line. Returns None for anything malformed."""
    parts = line.strip().split(",")
    if len(parts) != 2:
        return None
    try:
        angle, distance = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not 0 <= angle <= 180:
        return None
    return Reading(angle, distance)


class _ThreadedSource:
    name = "?"

    def __init__(self):
        self.error: str | None = None
        self._queue: queue.Queue[Reading] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)

    def poll(self) -> list[Reading]:
        """Return every reading received since the last poll."""
        readings = []
        while True:
            try:
                readings.append(self._queue.get_nowait())
            except queue.Empty:
                return readings

    def _run(self):
        raise NotImplementedError


class SerialSource(_ThreadedSource):
    def __init__(self, port: str, baud: int = 115200):
        super().__init__()
        self.port = port
        self.baud = baud
        self.name = port

    def _run(self):
        try:
            with serial.Serial(self.port, self.baud, timeout=0.5) as ser:
                time.sleep(2)  # opening the port resets the Uno; wait for it to boot
                ser.reset_input_buffer()
                while not self._stop.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    reading = parse_line(raw.decode("ascii", errors="ignore"))
                    if reading is not None:
                        self._queue.put(reading)
        except serial.SerialException as exc:
            self.error = str(exc)


class SimulatedSource(_ThreadedSource):
    """Fake Arduino. Sweeps past a few static targets, or with fixed=True stares
    straight ahead at one target drifting in and out."""

    # (centre angle, half width in degrees, distance cm)
    TARGETS = [(40, 6, 120), (95, 4, 60), (140, 8, 170)]

    def __init__(self, fixed: bool = False):
        super().__init__()
        self.fixed = fixed
        self.name = "SIMULATOR (fixed)" if fixed else "SIMULATOR"

    def _run(self):
        if self.fixed:
            self._run_fixed()
        else:
            self._run_sweep()

    def _run_fixed(self):
        start = time.monotonic()
        while not self._stop.is_set():
            t = time.monotonic() - start
            distance = 100 + 60 * math.sin(t / 3)
            if random.random() < 0.05:
                self._queue.put(Reading(90, -1))  # occasional dropout, like the real sensor
            else:
                self._queue.put(Reading(90, round(distance + random.gauss(0, 1.5))))
            time.sleep(0.06)

    def _run_sweep(self):
        angle, direction = 15, 1
        while not self._stop.is_set():
            distance = -1
            for centre, half_width, target_distance in self.TARGETS:
                if abs(angle - centre) <= half_width:
                    distance = round(target_distance + random.gauss(0, 2))
                    break
            self._queue.put(Reading(angle, distance))

            angle += direction * 2
            if angle >= 165 or angle <= 15:
                angle = max(15, min(165, angle))
                direction = -direction
            time.sleep(0.05)
