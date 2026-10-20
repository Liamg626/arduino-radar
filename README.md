# arduino-radar

A submarine-style sonar display. An Elegoo Uno R3 reads an HC-SR04 ultrasonic sensor (later swept by an SG90 servo) and streams readings over USB; a Python/pygame app draws them as blips on a radar screen.

## Hardware

| Part | Pin | Uno |
|---|---|---|
| HC-SR04 | VCC / GND | 5V / GND |
| HC-SR04 | Trig | D10 |
| HC-SR04 | Echo | D11 |
| SG90 servo | Red / Brown | 5V / GND |
| SG90 servo | Orange (signal) | D9 |

Put a 100–470 µF capacitor across the servo's 5V/GND. If the Uno resets or readings get noisy when the servo moves, power the servo from a separate 5V supply and connect its ground to the Uno's GND.

## Serial protocol

115200 baud, one line per reading:

```
<angle>,<distance_cm>
```

`angle` is the servo angle in degrees (0 = right, 90 = straight ahead, 180 = left). `distance_cm` is `-1` when there's no echo or the target is out of range (2–400 cm). The display shows angles as bearings: 000 ahead, 090 right, 270 left.

## Arduino

Open `arduino/radar/radar.ino` in the Arduino IDE, select **Arduino Uno** and the right COM port, and upload. Check the output in the Serial Monitor at 115200 baud, then **close the Serial Monitor**: only one program can use the port at a time.

- **Phase 1 (fixed sensor):** `#define USE_SERVO 0`. It always reports angle 90.
- **Phase 2 (sweeping):** mount the sensor on the servo and set `#define USE_SERVO 1`. It sweeps 15–165° in 2° steps.

## Python display

```
cd python
pip install -r requirements.txt

python main.py                     # lists available serial ports
python main.py --port COM3         # real hardware
python main.py --simulate          # fake sweeping sensor, no hardware needed
python main.py --simulate --fixed  # fake fixed sensor
```

Options: `--range 200` sets the display range in cm, `--persist 5` sets how many seconds blips take to fade, and `--baud` sets the baud rate. Press `Q` or `Esc` to quit.

When the port opens, the Uno resets, so the first readings appear after about 2 seconds.
