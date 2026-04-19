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
const unsigned long READY_PULSE_MS = 90;
const unsigned long READY_PERIOD_MS = 1600;
const unsigned long PROCESSING_BLINK_MS = 140;
const unsigned long RESULT_BLINK_MS = 120;

enum class LedMode {
  Ready,
  Listening,
  Processing,
  Result,
};

bool stablePressed = false;
bool lastRawPressed = false;
unsigned long lastEdgeMs = 0;
String serialLine;
LedMode ledMode = LedMode::Ready;
bool ledState = false;
unsigned long ledModeStartedMs = 0;
unsigned long lastLedStepMs = 0;
unsigned int resultBlinkTarget = 0;
unsigned int resultBlinkCount = 0;

void setLedOutput(bool on) {
  ledState = on;
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
}

void setLedMode(LedMode mode) {
  ledMode = mode;
  ledModeStartedMs = millis();
  lastLedStepMs = ledModeStartedMs;
  resultBlinkTarget = 0;
  resultBlinkCount = 0;

  if (mode == LedMode::Listening) {
    setLedOutput(true);
    return;
  }

  setLedOutput(false);
}

void triggerResult(unsigned int blinkCount) {
  ledMode = LedMode::Result;
  ledModeStartedMs = millis();
  lastLedStepMs = ledModeStartedMs;
  resultBlinkTarget = blinkCount;
  resultBlinkCount = 0;
  setLedOutput(false);
}

void updateStatusLed() {
  unsigned long now = millis();

  switch (ledMode) {
    case LedMode::Ready: {
      unsigned long phase = (now - ledModeStartedMs) % READY_PERIOD_MS;
      setLedOutput(phase < READY_PULSE_MS);
      break;
    }

    case LedMode::Listening:
      setLedOutput(true);
      break;

    case LedMode::Processing: {
      bool phaseOn = ((now - ledModeStartedMs) / PROCESSING_BLINK_MS) % 2 == 0;
      setLedOutput(phaseOn);
      break;
    }

    case LedMode::Result:
      if (resultBlinkCount >= resultBlinkTarget) {
        setLedMode(LedMode::Ready);
        break;
      }

      if ((now - lastLedStepMs) < RESULT_BLINK_MS) {
        break;
      }

      lastLedStepMs = now;
      if (!ledState) {
        setLedOutput(true);
      } else {
        setLedOutput(false);
        resultBlinkCount += 1;
        if (resultBlinkCount >= resultBlinkTarget) {
          setLedMode(LedMode::Ready);
        }
      }
      break;
  }
}

void emitEvent(const char* eventName) {
  Serial.println(eventName);
}

void applySerialCommand(const String& line) {
  if (line == "LISTENING") {
    setLedMode(LedMode::Listening);
    return;
  }

  if (line == "PROCESSING") {
    setLedMode(LedMode::Processing);
    return;
  }

  if (line == "IDLE" || line == "READY") {
    setLedMode(LedMode::Ready);
    return;
  }

  if (line.startsWith("RESULT ")) {
    triggerResult(2);
    return;
  }

  if (line == "ERROR") {
    triggerResult(4);
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
  setLedMode(LedMode::Ready);

  Serial.begin(SERIAL_BAUD);
  delay(400);
  Serial.println("GATEWAY_BOOT");
}

void loop() {
  updateStatusLed();
  pollSerialCommands();
  pollButton();
  delay(5);
}
