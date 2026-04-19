// ESP32 gateway firmware for button-driven push-to-talk over USB serial.
// Uses the onboard BOOT button (GPIO0 on most ESP32 dev boards).
// The RESET/EN button is not usable for app logic.

#include <string.h>
#include <WiFi.h>
#include <esp_now.h>

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

const uint8_t BROADCAST_ADDRESS[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

struct SwarmMessage {
  char command[16];
};

bool stablePressed = false;
bool lastRawPressed = false;
unsigned long lastEdgeMs = 0;
String serialLine;
bool swarmRadioReady = false;
esp_now_peer_info_t broadcastPeer = {};

bool initializeSwarmRadio() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP_NOW_INIT_FAILED");
    return false;
  }

  memcpy(broadcastPeer.peer_addr, BROADCAST_ADDRESS, sizeof(BROADCAST_ADDRESS));
  broadcastPeer.channel = 0;
  broadcastPeer.encrypt = false;

  if (esp_now_add_peer(&broadcastPeer) != ESP_OK) {
    Serial.println("ESP_NOW_PEER_FAILED");
    return false;
  }

  return true;
}

void sendSwarmPulse() {
  if (!swarmRadioReady) {
    return;
  }

  SwarmMessage message = {};
  strncpy(message.command, "SWARM", sizeof(message.command) - 1);

  esp_err_t result = esp_now_send(
    BROADCAST_ADDRESS,
    reinterpret_cast<const uint8_t*>(&message),
    sizeof(message)
  );

  if (result != ESP_OK) {
    Serial.println("SWARM_SEND_FAILED");
  }
}

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
  if (line == "S" || line == "s" || line == "SWARM") {
    sendSwarmPulse();
    return;
  }

  if (line == "LISTENING") {
    setListeningLed(true);
    return;
  }

  if (line == "IDLE" || line == "READY") {
    setListeningLed(false);
    return;
  }

  if (line == "RESULT" || line.startsWith("RESULT ")) {
    sendSwarmPulse();
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
  swarmRadioReady = initializeSwarmRadio();
  Serial.println("GATEWAY_BOOT");
}

void loop() {
  pollSerialCommands();
  pollButton();
  delay(5);
}
