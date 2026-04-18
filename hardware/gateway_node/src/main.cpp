// ESP32 gateway firmware for button-driven push-to-talk over USB serial.
// Uses the onboard BOOT button (GPIO0 on most ESP32 dev boards).
// The RESET/EN button is not usable for app logic.

#include <Arduino.h>

#ifndef PTT_BUTTON_PIN
#define PTT_BUTTON_PIN 0
#endif

#ifndef STATUS_LED_PIN
#ifdef LED_BUILTIN
#define STATUS_LED_PIN LED_BUILTIN
#else
#define STATUS_LED_PIN 2
#endif
#endif

const unsigned long SERIAL_BAUD = 115200;
const unsigned long DEBOUNCE_MS = 25;
const unsigned long RESULT_BLINK_MS = 120;

bool stablePressed = false;
bool lastRawPressed = false;
unsigned long lastEdgeMs = 0;
String serialLine;

void setListeningLed(bool on) {
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
}

void blinkResult(unsigned int count) {
  for (unsigned int i = 0; i < count; ++i) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(RESULT_BLINK_MS);
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(RESULT_BLINK_MS);
  }
}

void emitEvent(const char* eventName) {
  Serial.println(eventName);
}

void applySerialCommand(const String& line) {
  if (line == "LISTENING") {
    setListeningLed(true);
    return;
  }

  if (line == "IDLE" || line == "READY") {
    setListeningLed(false);
    return;
  }

  if (line.startsWith("RESULT ")) {
    setListeningLed(false);
    blinkResult(2);
    return;
  }

  if (line == "ERROR") {
    setListeningLed(false);
    blinkResult(4);
  }
}

void pollSerialCommands() {
  while (Serial.available() > 0) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\r') {
      continue;
    }

    if (ch == '\n') {
      if (serialLine.length() > 0) {
        applySerialCommand(serialLine);
        serialLine = "";
      }
      continue;
    }

    serialLine += ch;
    if (serialLine.length() > 64) {
      serialLine = "";
    }
  }
}

void pollButton() {
  bool rawPressed = digitalRead(PTT_BUTTON_PIN) == LOW;

  if (rawPressed != lastRawPressed) {
    lastRawPressed = rawPressed;
    lastEdgeMs = millis();
  }

  if ((millis() - lastEdgeMs) < DEBOUNCE_MS) {
    return;
  }

  if (rawPressed == stablePressed) {
    return;
  }

  stablePressed = rawPressed;
  if (stablePressed) {
    emitEvent("PTT_DOWN");
  } else {
    emitEvent("PTT_UP");
  }
}

void setup() {
  pinMode(PTT_BUTTON_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  Serial.begin(SERIAL_BAUD);
  delay(400);
  Serial.println("GATEWAY_BOOT");
}

void loop() {
  pollSerialCommands();
  pollButton();
  delay(5);
}
