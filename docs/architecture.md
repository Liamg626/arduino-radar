# Architecture

How the code fits together, from the Arduino ping to a pixel on screen. The same diagram is in [`diagrams/code-flow.mmd`](diagrams/code-flow.mmd) for any Mermaid viewer.

```mermaid
flowchart TB
    subgraph ARD["Arduino · arduino/radar/radar.ino"]
        Setup["setup()<br/>Serial.begin(115200), pinMode Trig / Echo<br/>servo.attach(9) if USE_SERVO"]
        Loop{"loop()<br/>USE_SERVO? (compile-time #if)"}
        Move["servo.write(angle)<br/>delay 30 ms to settle"]
        Read["readDistanceCm()<br/>Trig HIGH 10 µs → pulseIn(Echo, 25 ms timeout)<br/>cm = µs / 58 · -1 if timeout or outside 2–400"]
        Send["sendReading(angle, cm)<br/>Serial.println #quot;angle,cm#quot;<br/>180 - angle if MIRROR_ANGLE"]
        Next["angle ± 2°<br/>reverse direction at 15° / 165°"]
        Fixed["delay 60 ms<br/>angle fixed at 90"]
        Setup --> Loop
        Loop -- "1: sweep" --> Move --> Read
        Loop -- "0: fixed" --> Read
        Read --> Send
        Send -- sweep --> Next --> Loop
        Send -- fixed --> Fixed --> Loop
    end

    subgraph WORKER["Python worker thread · python/source.py"]
        Readline["SerialSource._run(): ser.readline()<br/>SimulatedSource fakes pings instead<br/>SerialException → source.error"]
        Parse["parse_line()<br/>#quot;angle,cm#quot; → Reading · None if malformed"]
        Put["queue.put(Reading)"]
        Readline --> Parse --> Put --> Readline
    end

    subgraph MAIN["Python main thread · python/main.py, 60 fps"]
        Poll["pygame.event.get(): Q / Esc / close → source.stop(), quit<br/>source.poll(): drain everything queued"]
        Update["RadarDisplay.update(reading)<br/>track angle + sweep direction<br/>echo within range → append Blip"]
        Poll --> Update
    end

    subgraph DRAW["draw() · display.py, contacts.py"]
        Expire["_expire_blips()<br/>drop blips older than persist_s"]
        Contacts["find_contacts()<br/>union-find: echoes within 6° and 15 cm<br/>groups of 3+ → Contact, range = median of 5 newest"]
        Layers["background → echo dots<br/>+ wide and tight blur glow (BLEND_ADD)<br/>→ sweep line and trail"]
        Labels["_draw_contacts(): 'NN cm' labels<br/>_draw_panel(): BRG · RNG · CONTACTS · NEAREST"]
        Flip["display.flip(), clock.tick(60)"]
        Expire --> Contacts --> Layers --> Labels --> Flip
    end

    Send == "USB serial, 115200 baud" ==> Readline
    Put -. "queue.Queue (thread-safe hand-off)" .-> Poll
    Update --> Expire
    Flip -. "next frame" .-> Poll

    style ARD fill:#fdf1e6,stroke:#c8580f
    style WORKER fill:#e8f1f8,stroke:#1f6496
    style MAIN fill:#e8f1f8,stroke:#1f6496
    style DRAW fill:#e7f5ec,stroke:#2f8a55
```

## Key points

- **Serial protocol:** one ASCII line per reading, `<angle>,<distance_cm>
` at 115200 baud. `-1` means no echo. This line is the only contract between the Arduino and Python.
- **Threads:** the serial read blocks, so it runs on a daemon worker thread (`_ThreadedSource`). The main thread never touches the port. It only drains the `queue.Queue` once per frame with `poll()`.
- **Sources are interchangeable:** `SerialSource` and `SimulatedSource` share the same `start()` / `poll()` / `stop()` / `error` interface, so `--simulate` exercises everything except the hardware.
- **State lives in `RadarDisplay`:** `update()` only appends a `Blip`. Expiry, grouping into `Contact`s and rendering all happen in `draw()`, so they run once per frame no matter how many readings arrived.
- **Rendering:** echoes are drawn on a black layer and added onto the screen with `BLEND_ADD`, along with two blurred copies for the glow. The background (rings, bearings) is rendered once in `__init__`.

## Where to change things

| To change | Edit |
|---|---|
| Sweep arc, step, speed, mirroring | Constants at the top of `arduino/radar/radar.ino` |
| Fixed vs sweeping sensor | `#define USE_SERVO` in `radar.ino` |
| What counts as one object | `ANGLE_GAP_DEG`, `DISTANCE_GAP_CM`, `MIN_HITS` in `python/contacts.py` |
| Dot size, glow, colours | Constants at the top of `python/display.py` |
| Display range, fade time | `--range`, `--persist` on `python/main.py` |
