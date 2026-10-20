# How it works

## System overview

```mermaid
flowchart LR
    subgraph Hardware
        Servo["SG90 servo<br/>(D9)"]
        Sensor["HC-SR04 sensor<br/>(Trig D10, Echo D11)"]
        Servo -. turns .-> Sensor
    end

    subgraph Uno["Arduino Uno - radar.ino"]
        Move["servo.write(angle)<br/>wait 30 ms"]
        Ping["Trig HIGH 10 µs"]
        Time["pulseIn(Echo)<br/>time in µs"]
        Calc["distance = time / 58<br/>(-1 if no echo)"]
        Send["Serial.println<br/>&quot;angle,distance&quot;"]
        Move --> Ping --> Time --> Calc --> Send
        Send -- "angle ± 2°" --> Move
    end

    subgraph PC["Laptop - python/"]
        Source["source.py<br/>read + parse line"]
        Contacts["contacts.py<br/>group nearby echoes"]
        Display["display.py<br/>draw sonar screen"]
        Source --> Contacts --> Display
    end

    Move --> Servo
    Ping --> Sensor
    Sensor -- "echo pulse" --> Time
    Send -- "USB serial<br/>115200 baud" --> Source
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
