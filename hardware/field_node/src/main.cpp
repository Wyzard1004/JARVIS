// ESP32 field node firmware for JARVIS relay demo.
// Supports two roles via PlatformIO environments:
// - field_relay: drone-1, relay-capable
// - field_leaf: drone-2, leaf endpoint

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

#include "relay_protocol.h"

#ifndef STATUS_LED_PIN
#ifdef LED_BUILTIN
#define STATUS_LED_PIN LED_BUILTIN
#else
#define STATUS_LED_PIN 2
#endif
#endif

#ifndef CURRENT_NODE_ID
#define CURRENT_NODE_ID RELAY_NODE_DRONE_1
#endif

#ifndef ENABLE_FORWARDING
#define ENABLE_FORWARDING 0
#endif

const unsigned long SERIAL_BAUD = 115200;
const unsigned long HEARTBEAT_PULSE_MS = 90;
const unsigned long HEARTBEAT_PERIOD_MS = 1600;
const unsigned long SHORT_BLINK_MS = 120;
const unsigned long LONG_BLINK_MS = 240;
const unsigned long ERROR_BLINK_MS = 70;
const unsigned long DUPLICATE_WINDOW_MS = 10000;
const size_t RADIO_RX_QUEUE_CAPACITY = 8;
const size_t SEEN_PACKET_CAPACITY = 16;

enum class LedMode {
  Heartbeat,
  Pattern,
};

struct RadioRxFrame {
  RelayPacketEncrypted packet;
};

struct SeenPacket {
  uint32_t packetId;
  unsigned long seenAtMs;
};

LedMode ledMode = LedMode::Heartbeat;
bool ledState = false;
unsigned long ledModeStartedMs = 0;
unsigned long ledLastStepMs = 0;
unsigned long patternOnMs = 0;
unsigned long patternOffMs = 0;
uint8_t patternTargetCycles = 0;
uint8_t patternCompletedCycles = 0;

RadioRxFrame radioQueue[RADIO_RX_QUEUE_CAPACITY];
volatile uint8_t radioQueueHead = 0;
volatile uint8_t radioQueueTail = 0;
portMUX_TYPE radioQueueMux = portMUX_INITIALIZER_UNLOCKED;

SeenPacket seenPackets[SEEN_PACKET_CAPACITY] = {};

constexpr uint8_t NODE_ID = CURRENT_NODE_ID;
constexpr bool NODE_CAN_FORWARD = (ENABLE_FORWARDING != 0);

void setLedOutput(bool on) {
  ledState = on;
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
}

void setHeartbeatMode() {
  ledMode = LedMode::Heartbeat;
  ledModeStartedMs = millis();
  ledLastStepMs = ledModeStartedMs;
  setLedOutput(false);
}

void startPattern(unsigned long onMs, unsigned long offMs, uint8_t cycles) {
  ledMode = LedMode::Pattern;
  ledModeStartedMs = millis();
  ledLastStepMs = ledModeStartedMs;
  patternOnMs = onMs;
  patternOffMs = offMs;
  patternTargetCycles = cycles;
  patternCompletedCycles = 0;
  setLedOutput(false);
}

void updateLed() {
  const unsigned long now = millis();
  if (ledMode == LedMode::Heartbeat) {
    const unsigned long phase = (now - ledModeStartedMs) % HEARTBEAT_PERIOD_MS;
    setLedOutput(phase < HEARTBEAT_PULSE_MS);
    return;
  }

  const unsigned long threshold = ledState ? patternOnMs : patternOffMs;
  if ((now - ledLastStepMs) < threshold) {
    return;
  }

  ledLastStepMs = now;
  if (!ledState) {
    setLedOutput(true);
    return;
  }

  setLedOutput(false);
  patternCompletedCycles += 1;
  if (patternCompletedCycles >= patternTargetCycles) {
    setHeartbeatMode();
  }
}

void playReceivePattern(uint8_t packetKind) {
  if (packetKind == RELAY_KIND_COMMAND_STAGED) {
    startPattern(SHORT_BLINK_MS, SHORT_BLINK_MS, 1);
    return;
  }

  if (packetKind == RELAY_KIND_COMMAND_DIRECT) {
    startPattern(SHORT_BLINK_MS, SHORT_BLINK_MS, 1);
    return;
  }

  if (packetKind == RELAY_KIND_COMMAND_EXECUTE) {
    startPattern(SHORT_BLINK_MS, SHORT_BLINK_MS, 3);
    return;
  }

  if (packetKind == RELAY_KIND_COMMAND_CANCEL) {
    startPattern(LONG_BLINK_MS, LONG_BLINK_MS, 2);
    return;
  }

  startPattern(ERROR_BLINK_MS, ERROR_BLINK_MS, 4);
}

void playForwardPattern() {
  startPattern(45, 45, 2);
}

void playErrorPattern() {
  startPattern(ERROR_BLINK_MS, ERROR_BLINK_MS, 4);
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

bool acceptsCommandFrom(uint8_t senderId) {
  if (NODE_ID == RELAY_NODE_DRONE_1) {
    return senderId == RELAY_NODE_SOLDIER_1;
  }

  if (NODE_ID == RELAY_NODE_DRONE_2) {
    return senderId == RELAY_NODE_DRONE_1;
  }

  return false;
}

bool hasRecentPacket(uint32_t packetId, unsigned long nowMs) {
  for (size_t index = 0; index < SEEN_PACKET_CAPACITY; ++index) {
    if (seenPackets[index].packetId == packetId && (nowMs - seenPackets[index].seenAtMs) <= DUPLICATE_WINDOW_MS) {
      return true;
    }
  }
  return false;
}

void rememberPacket(uint32_t packetId, unsigned long nowMs) {
  size_t oldestIndex = 0;
  unsigned long oldestSeen = seenPackets[0].seenAtMs;

  for (size_t index = 0; index < SEEN_PACKET_CAPACITY; ++index) {
    if (seenPackets[index].packetId == 0 || (nowMs - seenPackets[index].seenAtMs) > DUPLICATE_WINDOW_MS) {
      seenPackets[index].packetId = packetId;
      seenPackets[index].seenAtMs = nowMs;
      return;
    }

    if (seenPackets[index].seenAtMs < oldestSeen) {
      oldestSeen = seenPackets[index].seenAtMs;
      oldestIndex = index;
    }
  }

  seenPackets[oldestIndex].packetId = packetId;
  seenPackets[oldestIndex].seenAtMs = nowMs;
}

void sendStatusPacket(uint8_t statusCode, const RelayPacketPlain* sourcePacket = nullptr) {
  RelayPacketPlain status = {};
  status.version = RELAY_VERSION;
  status.kind = RELAY_KIND_STATUS;
  status.packet_id = sourcePacket ? sourcePacket->packet_id : 0;
  status.origin_id = NODE_ID;
  status.sender_id = NODE_ID;
  status.target_id = RELAY_NODE_SOLDIER_1;
  status.goal = sourcePacket ? sourcePacket->goal : RELAY_GOAL_NONE;
  status.execution_state = statusCode;
  status.priority = sourcePacket ? sourcePacket->priority : RELAY_PRIORITY_LOW;
  status.target_code = sourcePacket ? sourcePacket->target_code : 0;
  status.hop_count = sourcePacket ? sourcePacket->hop_count : 0;
  status.max_hops = sourcePacket ? sourcePacket->max_hops : 0;
  status.flags = 0;
  status.issued_at_s = 0;
  status.expires_at_s = sourcePacket
    ? (sourcePacket->expires_at_s > 0 ? sourcePacket->expires_at_s : 1)
    : 5;
  relayBroadcastPacket(status);
}

void sendAckPacket(const RelayPacketPlain& sourcePacket) {
  RelayPacketPlain ack = {};
  ack.version = RELAY_VERSION;
  ack.kind = RELAY_KIND_ACK;
  ack.packet_id = sourcePacket.packet_id;
  ack.origin_id = NODE_ID;
  ack.sender_id = NODE_ID;
  ack.target_id = RELAY_NODE_SOLDIER_1;
  ack.goal = sourcePacket.goal;
  ack.execution_state = sourcePacket.execution_state;
  ack.priority = sourcePacket.priority;
  ack.target_code = sourcePacket.target_code;
  ack.hop_count = sourcePacket.hop_count;
  ack.max_hops = sourcePacket.max_hops;
  ack.flags = 0;
  ack.issued_at_s = 0;
  ack.expires_at_s = sourcePacket.expires_at_s > 0 ? sourcePacket.expires_at_s : 1;
  relayBroadcastPacket(ack);
}

uint8_t statusCodeForPacketKind(uint8_t packetKind) {
  if (packetKind == RELAY_KIND_COMMAND_STAGED) return RELAY_STATUS_RECEIVED_STAGED;
  if (packetKind == RELAY_KIND_COMMAND_DIRECT) return RELAY_STATUS_RECEIVED_COMMAND;
  if (packetKind == RELAY_KIND_COMMAND_EXECUTE) return RELAY_STATUS_RECEIVED_EXECUTE;
  if (packetKind == RELAY_KIND_COMMAND_CANCEL) return RELAY_STATUS_RECEIVED_CANCEL;
  return RELAY_STATUS_ERROR;
}

bool shouldForwardPacket(const RelayPacketPlain& packet) {
  return NODE_CAN_FORWARD &&
         (packet.flags & RELAY_FLAG_FORWARDABLE) != 0 &&
         packet.hop_count < packet.max_hops &&
         NODE_ID == RELAY_NODE_DRONE_1;
}

void forwardPacket(const RelayPacketPlain& packet) {
  RelayPacketPlain forwarded = packet;
  forwarded.sender_id = NODE_ID;
  forwarded.hop_count = static_cast<uint8_t>(packet.hop_count + 1);

  const unsigned long backoffMs = static_cast<unsigned long>(random(30, 91));
  delay(backoffMs);

  if (relayBroadcastPacket(forwarded)) {
    sendStatusPacket(RELAY_STATUS_FORWARDED, &forwarded);
    playForwardPattern();
  } else {
    sendStatusPacket(RELAY_STATUS_ERROR, &forwarded);
    playErrorPattern();
  }
}

void processCommandPacket(const RelayPacketPlain& packet) {
  if (packet.version != RELAY_VERSION) {
    playErrorPattern();
    return;
  }

  if (packet.kind != RELAY_KIND_COMMAND_STAGED &&
      packet.kind != RELAY_KIND_COMMAND_DIRECT &&
      packet.kind != RELAY_KIND_COMMAND_EXECUTE &&
      packet.kind != RELAY_KIND_COMMAND_CANCEL) {
    return;
  }

  if (!acceptsCommandFrom(packet.sender_id)) {
    return;
  }

  if (packet.expires_at_s == 0) {
    playErrorPattern();
    sendStatusPacket(RELAY_STATUS_ERROR, &packet);
    return;
  }

  const unsigned long nowMs = millis();
  if (hasRecentPacket(packet.packet_id, nowMs)) {
    return;
  }
  rememberPacket(packet.packet_id, nowMs);

  playReceivePattern(packet.kind);
  sendStatusPacket(statusCodeForPacketKind(packet.kind), &packet);
  sendAckPacket(packet);

  if (shouldForwardPacket(packet)) {
    forwardPacket(packet);
  }
}

void processRadioFrames() {
  RelayPacketEncrypted encrypted = {};
  while (dequeueRadioFrame(encrypted)) {
    RelayPacketPlain plain = {};
    if (!relayDecryptPacket(encrypted, plain)) {
      playErrorPattern();
      continue;
    }

    if (plain.kind == RELAY_KIND_COMMAND_STAGED ||
        plain.kind == RELAY_KIND_COMMAND_DIRECT ||
        plain.kind == RELAY_KIND_COMMAND_EXECUTE ||
        plain.kind == RELAY_KIND_COMMAND_CANCEL) {
      processCommandPacket(plain);
    }
  }
}

void setupRadio() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("FIELD_NODE_ERROR ESPNOW_INIT");
    return;
  }

  if (!relayEnsureBroadcastPeer()) {
    Serial.println("FIELD_NODE_ERROR PEER_INIT");
  }

  esp_now_register_recv_cb(onEspNowReceive);
}

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  setHeartbeatMode();
  Serial.begin(SERIAL_BAUD);
  delay(400);

  Serial.printf(
    "FIELD_NODE_BOOT %s forwarding=%s\n",
    relayNodeName(NODE_ID),
    NODE_CAN_FORWARD ? "true" : "false"
  );

  randomSeed(static_cast<uint32_t>(esp_random()));
  setupRadio();
  delay(150);
  sendStatusPacket(RELAY_STATUS_READY, nullptr);
}

void loop() {
  updateLed();
  processRadioFrames();
  delay(5);
}
