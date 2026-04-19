// ESP32 gateway firmware for button-driven push-to-talk over USB serial
// plus ESP-NOW relay broadcast to field nodes.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <esp_now.h>
#include <mbedtls/base64.h>
#include <memory>

#include "relay_protocol.h"

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
const size_t MAX_SERIAL_LINE = 768;
const size_t RADIO_RX_QUEUE_CAPACITY = 8;

enum class LedMode {
  Ready,
  Listening,
  Processing,
  Result,
};

struct RadioRxFrame {
  RelayPacketEncrypted packet;
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

RadioRxFrame radioQueue[RADIO_RX_QUEUE_CAPACITY];
volatile uint8_t radioQueueHead = 0;
volatile uint8_t radioQueueTail = 0;
portMUX_TYPE radioQueueMux = portMUX_INITIALIZER_UNLOCKED;

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

void emitAck(const RelayPacketPlain& packet) {
  Serial.printf(
    "ACK %lu %s %u\n",
    static_cast<unsigned long>(packet.packet_id),
    relayNodeName(packet.sender_id),
    static_cast<unsigned int>(packet.hop_count)
  );
}

void emitStatus(const RelayPacketPlain& packet) {
  Serial.printf(
    "STATUS %s %s\n",
    relayNodeName(packet.sender_id),
    relayStatusName(packet.execution_state)
  );
}

String normalizeToken(const String& input) {
  String normalized;
  normalized.reserve(input.length());
  for (size_t index = 0; index < input.length(); ++index) {
    char ch = input[index];
    if (ch == ' ' || ch == '-') {
      normalized += '_';
    } else {
      normalized += static_cast<char>(toupper(static_cast<unsigned char>(ch)));
    }
  }
  return normalized;
}

uint8_t packetKindFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "COMMAND_STAGED") return RELAY_KIND_COMMAND_STAGED;
  if (normalized == "COMMAND_EXECUTE") return RELAY_KIND_COMMAND_EXECUTE;
  if (normalized == "COMMAND_CANCEL") return RELAY_KIND_COMMAND_CANCEL;
  if (normalized == "ACK") return RELAY_KIND_ACK;
  if (normalized == "STATUS") return RELAY_KIND_STATUS;
  return RELAY_KIND_UNKNOWN;
}

uint8_t nodeIdFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "SOLDIER_1") return RELAY_NODE_SOLDIER_1;
  if (normalized == "DRONE_1") return RELAY_NODE_DRONE_1;
  if (normalized == "DRONE_2") return RELAY_NODE_DRONE_2;
  return RELAY_NODE_UNKNOWN;
}

uint8_t goalFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "ATTACK_AREA") return RELAY_GOAL_ATTACK_AREA;
  if (normalized == "SCAN_AREA") return RELAY_GOAL_SCAN_AREA;
  if (normalized == "MARK") return RELAY_GOAL_MARK;
  if (normalized == "MOVE_TO") return RELAY_GOAL_MOVE_TO;
  if (normalized == "AVOID_AREA") return RELAY_GOAL_AVOID_AREA;
  if (normalized == "HOLD_POSITION") return RELAY_GOAL_HOLD_POSITION;
  if (normalized == "LOITER") return RELAY_GOAL_LOITER;
  if (normalized == "STANDBY") return RELAY_GOAL_STANDBY;
  if (normalized == "EXECUTE") return RELAY_GOAL_EXECUTE;
  if (normalized == "DISREGARD") return RELAY_GOAL_DISREGARD;
  if (normalized == "ABORT") return RELAY_GOAL_ABORT;
  if (normalized == "NO_OP") return RELAY_GOAL_NO_OP;
  return RELAY_GOAL_NONE;
}

uint8_t executionStateFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "PENDING_EXECUTE") return RELAY_EXEC_PENDING;
  if (normalized == "EXECUTED") return RELAY_EXEC_EXECUTED;
  if (normalized == "CANCELED" || normalized == "CANCELLED") return RELAY_EXEC_CANCELED;
  return RELAY_EXEC_NONE;
}

uint8_t priorityFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "HIGH") return RELAY_PRIORITY_HIGH;
  if (normalized == "LOW") return RELAY_PRIORITY_LOW;
  return RELAY_PRIORITY_MEDIUM;
}

uint8_t targetCodeFromString(const String& value) {
  const String normalized = normalizeToken(value);
  if (normalized == "GRID_ALPHA") return 1;
  if (normalized == "GRID_ALPHA_1") return 2;
  if (normalized == "GRID_ALPHA_2") return 3;
  if (normalized == "GRID_ALPHA_3") return 4;
  if (normalized == "GRID_BRAVO") return 5;
  if (normalized == "GRID_BRAVO_1") return 6;
  if (normalized == "GRID_BRAVO_2") return 7;
  if (normalized == "GRID_BRAVO_3") return 8;
  if (normalized == "GRID_CHARLIE") return 9;
  if (normalized == "GRID_CHARLIE_1") return 10;
  if (normalized == "GRID_CHARLIE_2") return 11;
  if (normalized == "GRID_CHARLIE_3") return 12;
  return 0;
}

bool decodeBase64String(const String& encoded, String& decoded) {
  size_t outputLength = 0;
  const size_t bufferSize = ((encoded.length() + 3) / 4) * 3 + 4;
  std::unique_ptr<unsigned char[]> buffer(new unsigned char[bufferSize]);

  const int rc = mbedtls_base64_decode(
    buffer.get(),
    bufferSize,
    &outputLength,
    reinterpret_cast<const unsigned char*>(encoded.c_str()),
    encoded.length()
  );

  if (rc != 0) {
    return false;
  }

  buffer[outputLength] = '\0';
  decoded = String(reinterpret_cast<const char*>(buffer.get()));
  return true;
}

uint32_t ttlSecondsFromJson(uint64_t issuedAtMs, uint64_t expiresAtMs) {
  if (expiresAtMs <= issuedAtMs) {
    return 0;
  }

  const uint64_t ttlMs = expiresAtMs - issuedAtMs;
  return static_cast<uint32_t>((ttlMs + 999ULL) / 1000ULL);
}

bool handleRelaySerialPayload(const String& encodedPayload) {
  String decodedJson;
  if (!decodeBase64String(encodedPayload, decodedJson)) {
    Serial.println("RELAY_ERR BASE64");
    return false;
  }

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, decodedJson);
  if (error) {
    Serial.println("RELAY_ERR JSON");
    return false;
  }

  RelayPacketPlain packet = {};
  packet.version = RELAY_VERSION;
  packet.kind = packetKindFromString(String(doc["packet_kind"] | ""));
  packet.packet_id = static_cast<uint32_t>(doc["packet_id"] | 0U);
  packet.origin_id = nodeIdFromString(String(doc["origin_node"] | "soldier-1"));
  if (packet.origin_id == RELAY_NODE_UNKNOWN) {
    packet.origin_id = RELAY_NODE_SOLDIER_1;
  }
  packet.sender_id = RELAY_NODE_SOLDIER_1;
  packet.target_id = RELAY_NODE_UNKNOWN;
  packet.goal = goalFromString(String(doc["goal"] | ""));
  packet.execution_state = executionStateFromString(String(doc["execution_state"] | "NONE"));
  packet.priority = priorityFromString(String(doc["priority"] | "medium"));
  packet.target_code = targetCodeFromString(String(doc["target_location"] | ""));
  packet.hop_count = 0;
  packet.max_hops = static_cast<uint8_t>(doc["max_hops"] | 2U);
  packet.flags = 0;
  if (static_cast<bool>(doc["ack_required"] | true)) {
    packet.flags |= RELAY_FLAG_ACK_REQUIRED;
  }
  if (packet.kind == RELAY_KIND_COMMAND_STAGED || packet.kind == RELAY_KIND_COMMAND_EXECUTE || packet.kind == RELAY_KIND_COMMAND_CANCEL) {
    packet.flags |= RELAY_FLAG_FORWARDABLE;
  }

  const uint64_t issuedAtMs = static_cast<uint64_t>(doc["issued_at_ms"] | 0ULL);
  const uint64_t expiresAtMs = static_cast<uint64_t>(doc["expires_at_ms"] | 0ULL);
  packet.issued_at_s = 0;
  packet.expires_at_s = ttlSecondsFromJson(issuedAtMs, expiresAtMs);

  if (packet.kind == RELAY_KIND_UNKNOWN || packet.packet_id == 0 || packet.expires_at_s == 0) {
    Serial.println("RELAY_ERR BAD_PACKET");
    return false;
  }

  if (!relayBroadcastPacket(packet)) {
    Serial.println("RELAY_ERR TX_FAIL");
    return false;
  }

  return true;
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
    return;
  }

  if (line.startsWith("RELAY ")) {
    if (!handleRelaySerialPayload(line.substring(6))) {
      triggerResult(4);
    }
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
    if (serialLine.length() > MAX_SERIAL_LINE) {
      serialLine = "";
      Serial.println("RELAY_ERR SERIAL_OVERFLOW");
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

bool enqueueRadioFrame(const uint8_t* data, int length) {
  if (length != static_cast<int>(sizeof(RelayPacketEncrypted))) {
    return false;
  }

  bool queued = false;
  portENTER_CRITICAL(&radioQueueMux);
  uint8_t nextHead = static_cast<uint8_t>((radioQueueHead + 1) % RADIO_RX_QUEUE_CAPACITY);
  if (nextHead != radioQueueTail) {
    memcpy(&radioQueue[radioQueueHead].packet, data, sizeof(RelayPacketEncrypted));
    radioQueueHead = nextHead;
    queued = true;
  }
  portEXIT_CRITICAL(&radioQueueMux);

  return queued;
}

bool dequeueRadioFrame(RelayPacketEncrypted& packet) {
  bool available = false;
  portENTER_CRITICAL(&radioQueueMux);
  if (radioQueueTail != radioQueueHead) {
    memcpy(&packet, &radioQueue[radioQueueTail].packet, sizeof(RelayPacketEncrypted));
    radioQueueTail = static_cast<uint8_t>((radioQueueTail + 1) % RADIO_RX_QUEUE_CAPACITY);
    available = true;
  }
  portEXIT_CRITICAL(&radioQueueMux);
  return available;
}

void onEspNowReceive(const uint8_t* /*macAddr*/, const uint8_t* data, int len) {
  enqueueRadioFrame(data, len);
}

void processRadioFrames() {
  RelayPacketEncrypted encrypted = {};
  while (dequeueRadioFrame(encrypted)) {
    RelayPacketPlain plain = {};
    if (!relayDecryptPacket(encrypted, plain)) {
      Serial.println("RELAY_ERR DECRYPT");
      continue;
    }

    if (plain.target_id != RELAY_NODE_UNKNOWN && plain.target_id != RELAY_NODE_SOLDIER_1) {
      continue;
    }

    if (plain.kind == RELAY_KIND_ACK) {
      emitAck(plain);
      continue;
    }

    if (plain.kind == RELAY_KIND_STATUS) {
      emitStatus(plain);
    }
  }
}

void setupRadio() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("RELAY_ERR ESPNOW_INIT");
    return;
  }

  if (!relayEnsureBroadcastPeer()) {
    Serial.println("RELAY_ERR PEER_INIT");
  }

  esp_now_register_recv_cb(onEspNowReceive);
}

void setup() {
  pinMode(PTT_BUTTON_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED_PIN, OUTPUT);
  setLedMode(LedMode::Ready);

  Serial.begin(SERIAL_BAUD);
  delay(400);
  Serial.println("GATEWAY_BOOT");
  setupRadio();
}

void loop() {
  updateStatusLed();
  pollSerialCommands();
  processRadioFrames();
  pollButton();
  delay(5);
}
