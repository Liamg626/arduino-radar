# How it works

Each diagram is also in `docs/diagrams/` as a standalone `.mmd` file, so it opens in any Mermaid viewer or at mermaid.live.

## System overview

Orange steps happen in the hardware, blue on the Arduino, and green on the laptop.

```mermaid
flowchart TB
    Move["<b>Servo</b> turns the sensor to the next angle<br/>servo.write(angle), wait 30 ms"]
    Ping["<b>Arduino</b> pulses Trig (D10) for 10 µs"]
    Sound["<b>HC-SR04</b> sends 8 bursts of 40 kHz sound"]
    Echo["Sound bounces off an object<br/>Echo (D11) stays HIGH for the round trip"]
    Calc["<b>Arduino</b> times it with pulseIn()<br/>distance = time ÷ 58 cm, or -1 if no echo"]
    Send["<b>Arduino</b> prints #quot;angle,distance#quot;<br/>USB serial, 115200 baud"]
    Parse["<b>source.py</b> reads and parses the line"]
    Group["<b>contacts.py</b> groups nearby echoes into objects"]
    Draw["<b>display.py</b> draws dots and range labels<br/>on the sonar screen"]

    Move --> Ping --> Sound --> Echo --> Calc --> Send --> Parse --> Group --> Draw
    Send -. "angle ± 2°, repeat<br/>(sweeps 15° to 165° and back)" .-> Move

    classDef hardware fill:#fdebd9,stroke:#c8580f,color:#13222a
    classDef arduino fill:#dbe8f2,stroke:#1f6496,color:#13222a
    classDef laptop fill:#dff3e6,stroke:#2f8a55,color:#13222a
    class Move,Sound,Echo hardware
    class Ping,Calc,Send arduino
    class Parse,Group,Draw laptop
```

## One ping, step by step

```mermaid
sequenceDiagram
    participant Uno as Arduino
    participant Servo
    participant Sensor as HC-SR04
    participant Py as Python

    Uno->>Servo: write(angle)
    Note over Servo: 30 ms to settle
    Uno->>Sensor: Trig HIGH for 10 µs
    Sensor->>Sensor: 8 × 40 kHz bursts out
    Note over Sensor: sound hits object<br/>and bounces back
    Sensor-->>Uno: Echo HIGH for round-trip time
    Uno->>Uno: distance = time / 58
    Uno->>Py: "90,123\n" over USB
    Py->>Py: angle + distance → x, y
    Py->>Py: draw dot, group into contacts, label range
    Uno->>Uno: angle += 2° (reverse at 15° / 165°)
```

## Why divide by 58?

Sound travels at about 343 m/s, which is 0.0343 cm/µs. It covers 1 cm in about 29.15 µs, and the pulse goes there and back, so each centimetre of distance adds 2 × 29.15 ≈ 58 µs to the echo time.
