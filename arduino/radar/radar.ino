// Arduino sonar: HC-SR04 ultrasonic sensor, optionally swept by an SG90 servo.
//
// Sends one line per reading over serial at 115200 baud:
//   <angle>,<distance_cm>     e.g. "90,123"
// A distance of -1 means no echo / out of range.
//
// Phase 1: USE_SERVO 0 -> sensor fixed, angle always reported as FIXED_ANGLE.
// Phase 3: USE_SERVO 1 -> sensor mounted on the servo, sweeping MIN..MAX_ANGLE.

#define USE_SERVO 1

#if USE_SERVO
#include <Servo.h>
#endif

const uint8_t TRIG_PIN = 10;
const uint8_t ECHO_PIN = 11;
const uint8_t SERVO_PIN = 9;

const int FIXED_ANGLE = 90;   // straight ahead
const int MIN_ANGLE = 15;     // SG90 strains at its 0/180 end stops
const int MAX_ANGLE = 165;
const int ANGLE_STEP = 2;
const bool MIRROR_ANGLE = false;  // set true if objects on your right show up on the left

const unsigned long ECHO_TIMEOUT_US = 25000UL;  // ~4.3 m round trip
const long MIN_DISTANCE_CM = 2;
const long MAX_DISTANCE_CM = 400;
const unsigned int SERVO_SETTLE_MS = 30;  // time for the servo to reach the new angle
const unsigned int FIXED_CYCLE_MS = 60;   // HC-SR04 datasheet recommends >= 60 ms between pings

#if USE_SERVO
Servo servo;
int angle = MIN_ANGLE;
int direction = 1;
#endif

long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) {
    return -1;  // timed out: nothing in range
  }

  // Sound travels ~0.0343 cm/us and the pulse covers the distance twice.
  long cm = duration / 58;
  if (cm < MIN_DISTANCE_CM || cm > MAX_DISTANCE_CM) {
    return -1;
  }
  return cm;
}

void sendReading(int readingAngle, long distanceCm) {
  Serial.print(MIRROR_ANGLE ? 180 - readingAngle : readingAngle);
  Serial.print(',');
  Serial.println(distanceCm);
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

#if USE_SERVO
  servo.attach(SERVO_PIN);
  servo.write(angle);
  delay(500);  // let it reach the start position
#endif
}

void loop() {
#if USE_SERVO
  servo.write(angle);
  delay(SERVO_SETTLE_MS);
  sendReading(angle, readDistanceCm());

  angle += direction * ANGLE_STEP;
  if (angle >= MAX_ANGLE || angle <= MIN_ANGLE) {
    angle = constrain(angle, MIN_ANGLE, MAX_ANGLE);
    direction = -direction;
  }
#else
  sendReading(FIXED_ANGLE, readDistanceCm());
  delay(FIXED_CYCLE_MS);
#endif
}
