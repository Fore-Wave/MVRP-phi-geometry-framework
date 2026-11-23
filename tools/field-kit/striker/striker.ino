// MVRP edge test: servo striker for the bowl and a matched cushion.
// Wiring: bowl servo signal -> pin 9, cushion servo signal -> pin 10,
//         both servos' power from a separate 5 V supply (common ground with the Arduino).
// Serial 115200: 'B' strikes the bowl, 'C' strikes the cushion; replies "K" when done.
// Two identical servos make the same motor sound, so A/B sound like C/D apart from the bowl itself.
#include <Servo.h>

Servo bowl, cushion;
const int REST = 90;        // mallet raised
const int HIT_BOWL = 125;   // adjust so the mallet just reaches the bowl rim
const int HIT_CUSH = 125;   // adjust so the cushion mallet travels the same distance
const int HOLD_MS = 120;    // contact time; keep it the same for both

void strike(Servo &s, int hit) {
  s.write(hit);
  delay(HOLD_MS);
  s.write(REST);
  delay(250);
}

void setup() {
  Serial.begin(115200);
  bowl.attach(9);
  cushion.attach(10);
  bowl.write(REST);
  cushion.write(REST);
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'B') { strike(bowl, HIT_BOWL); Serial.println("K"); }
    else if (c == 'C') { strike(cushion, HIT_CUSH); Serial.println("K"); }
  }
}
