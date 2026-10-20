// Servo test and centring helper.
//
// Swings the servo to 15, 90 and 165 degrees once so you can check it moves,
// then parks it at 90 (straight ahead). Attach the horn + sensor facing
// forwards while it's parked, then upload radar.ino.

#include <Servo.h>

const uint8_t SERVO_PIN = 9;

Servo servo;

void setup() {
  Serial.begin(115200);
  servo.attach(SERVO_PIN);

  const int positions[] = {90, 15, 90, 165, 90};
  for (int angle : positions) {
    Serial.print("Moving to ");
    Serial.println(angle);
    servo.write(angle);
    delay(1000);
  }
  Serial.println("Parked at 90 - attach the sensor facing straight ahead.");
}

void loop() {
}
