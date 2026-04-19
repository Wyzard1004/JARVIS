#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>
#include <mbedtls/gcm.h>

static constexpr uint8_t RELAY_SHARED_KEY[32] = {
    0x4A, 0x41, 0x52, 0x56, 0x49, 0x53, 0x2D, 0x52,
    0x45, 0x4C, 0x41, 0x59, 0x2D, 0x44, 0x45, 0x4D,
    0x4F, 0x2D, 0x4B, 0x45, 0x59, 0x2D, 0x32, 0x30,
    0x32, 0x36, 0x2D, 0x41, 0x45, 0x53, 0x21, 0x21,
};

static constexpr uint8_t RELAY_BROADCAST_ADDRESS[6] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
};

static constexpr uint8_t RELAY_VERSION = 1;
static constexpr size_t RELAY_NONCE_BYTES = 12;
static constexpr size_t RELAY_TAG_BYTES = 16;
static constexpr uint8_t RELAY_KEY_ID = 1;

enum RelayNodeId : uint8_t {
  RELAY_NODE_UNKNOWN = 0,
  RELAY_NODE_SOLDIER_1 = 1,
  RELAY_NODE_DRONE_1 = 2,
  RELAY_NODE_DRONE_2 = 3,
};

enum RelayPacketKind : uint8_t {
  RELAY_KIND_UNKNOWN = 0,
  RELAY_KIND_COMMAND_STAGED = 1,
  RELAY_KIND_COMMAND_EXECUTE = 2,
  RELAY_KIND_COMMAND_CANCEL = 3,
  RELAY_KIND_ACK = 4,
  RELAY_KIND_STATUS = 5,
  RELAY_KIND_COMMAND_DIRECT = 6,
};

enum RelayGoalCode : uint8_t {
  RELAY_GOAL_NONE = 0,
  RELAY_GOAL_ATTACK_AREA = 1,
  RELAY_GOAL_SCAN_AREA = 2,
  RELAY_GOAL_MARK = 3,
  RELAY_GOAL_MOVE_TO = 4,
  RELAY_GOAL_AVOID_AREA = 5,
  RELAY_GOAL_HOLD_POSITION = 6,
  RELAY_GOAL_LOITER = 7,
  RELAY_GOAL_STANDBY = 8,
  RELAY_GOAL_EXECUTE = 9,
  RELAY_GOAL_DISREGARD = 10,
  RELAY_GOAL_ABORT = 11,
  RELAY_GOAL_NO_OP = 12,
};

enum RelayExecutionStateCode : uint8_t {
  RELAY_EXEC_NONE = 0,
  RELAY_EXEC_PENDING = 1,
  RELAY_EXEC_EXECUTED = 2,
  RELAY_EXEC_CANCELED = 3,
};

enum RelayPriorityCode : uint8_t {
  RELAY_PRIORITY_LOW = 0,
  RELAY_PRIORITY_MEDIUM = 1,
  RELAY_PRIORITY_HIGH = 2,
};

enum RelayStatusCode : uint8_t {
  RELAY_STATUS_NONE = 0,
  RELAY_STATUS_READY = 1,
  RELAY_STATUS_RECEIVED_STAGED = 2,
  RELAY_STATUS_RECEIVED_EXECUTE = 3,
  RELAY_STATUS_RECEIVED_CANCEL = 4,
  RELAY_STATUS_FORWARDED = 5,
  RELAY_STATUS_ERROR = 6,
  RELAY_STATUS_RECEIVED_COMMAND = 7,
};

static constexpr uint8_t RELAY_FLAG_ACK_REQUIRED = 0x01;
static constexpr uint8_t RELAY_FLAG_FORWARDABLE = 0x02;

#pragma pack(push, 1)
struct RelayPacketPlain {
  uint8_t version;
  uint8_t kind;
  uint32_t packet_id;
  uint8_t origin_id;
  uint8_t sender_id;
  uint8_t target_id;
  uint8_t goal;
  uint8_t execution_state;
  uint8_t priority;
  uint8_t target_code;
  uint8_t hop_count;
  uint8_t max_hops;
  uint8_t flags;
  uint32_t issued_at_s;
  uint32_t expires_at_s;
};

struct RelayPacketEncrypted {
  uint8_t key_id;
  uint8_t nonce[RELAY_NONCE_BYTES];
  uint8_t ciphertext[sizeof(RelayPacketPlain)];
  uint8_t tag[RELAY_TAG_BYTES];
};
#pragma pack(pop)

inline const char* relayNodeName(uint8_t node_id) {
  switch (node_id) {
    case RELAY_NODE_SOLDIER_1:
      return "soldier-1";
    case RELAY_NODE_DRONE_1:
      return "drone-1";
    case RELAY_NODE_DRONE_2:
      return "drone-2";
    default:
      return "unknown";
  }
}

inline const char* relayStatusName(uint8_t status_code) {
  switch (status_code) {
    case RELAY_STATUS_READY:
      return "READY";
    case RELAY_STATUS_RECEIVED_STAGED:
      return "RECEIVED_STAGED";
    case RELAY_STATUS_RECEIVED_EXECUTE:
      return "RECEIVED_EXECUTE";
    case RELAY_STATUS_RECEIVED_CANCEL:
      return "RECEIVED_CANCEL";
    case RELAY_STATUS_RECEIVED_COMMAND:
      return "RECEIVED_COMMAND";
    case RELAY_STATUS_FORWARDED:
      return "FORWARDED";
    case RELAY_STATUS_ERROR:
      return "ERROR";
    default:
      return "UNKNOWN";
  }
}

inline bool relayEnsureBroadcastPeer() {
  static bool peer_added = false;
  if (peer_added) {
    return true;
  }

  esp_now_peer_info_t peer_info = {};
  memcpy(peer_info.peer_addr, RELAY_BROADCAST_ADDRESS, sizeof(RELAY_BROADCAST_ADDRESS));
  peer_info.channel = 0;
  peer_info.encrypt = false;

  if (esp_now_add_peer(&peer_info) != ESP_OK && !esp_now_is_peer_exist(RELAY_BROADCAST_ADDRESS)) {
    return false;
  }

  peer_added = true;
  return true;
}

inline void relayFillNonce(uint8_t* nonce_bytes) {
  esp_fill_random(nonce_bytes, RELAY_NONCE_BYTES);
}

inline bool relayEncryptPacket(const RelayPacketPlain& plain, RelayPacketEncrypted& encrypted) {
  encrypted.key_id = RELAY_KEY_ID;
  relayFillNonce(encrypted.nonce);

  mbedtls_gcm_context context;
  mbedtls_gcm_init(&context);

  bool ok = false;
  if (mbedtls_gcm_setkey(&context, MBEDTLS_CIPHER_ID_AES, RELAY_SHARED_KEY, 256) == 0) {
    ok = (
      mbedtls_gcm_crypt_and_tag(
        &context,
        MBEDTLS_GCM_ENCRYPT,
        sizeof(RelayPacketPlain),
        encrypted.nonce,
        RELAY_NONCE_BYTES,
        nullptr,
        0,
        reinterpret_cast<const unsigned char*>(&plain),
        encrypted.ciphertext,
        RELAY_TAG_BYTES,
        encrypted.tag
      ) == 0
    );
  }

  mbedtls_gcm_free(&context);
  return ok;
}

inline bool relayDecryptPacket(const RelayPacketEncrypted& encrypted, RelayPacketPlain& plain) {
  if (encrypted.key_id != RELAY_KEY_ID) {
    return false;
  }

  mbedtls_gcm_context context;
  mbedtls_gcm_init(&context);

  bool ok = false;
  if (mbedtls_gcm_setkey(&context, MBEDTLS_CIPHER_ID_AES, RELAY_SHARED_KEY, 256) == 0) {
    ok = (
      mbedtls_gcm_auth_decrypt(
        &context,
        sizeof(RelayPacketPlain),
        encrypted.nonce,
        RELAY_NONCE_BYTES,
        nullptr,
        0,
        encrypted.tag,
        RELAY_TAG_BYTES,
        encrypted.ciphertext,
        reinterpret_cast<unsigned char*>(&plain)
      ) == 0
    );
  }

  mbedtls_gcm_free(&context);
  return ok;
}

inline bool relayBroadcastPacket(const RelayPacketPlain& plain) {
  RelayPacketEncrypted encrypted = {};
  if (!relayEncryptPacket(plain, encrypted)) {
    return false;
  }

  if (!relayEnsureBroadcastPeer()) {
    return false;
  }

  return esp_now_send(
    RELAY_BROADCAST_ADDRESS,
    reinterpret_cast<const uint8_t*>(&encrypted),
    sizeof(RelayPacketEncrypted)
  ) == ESP_OK;
}
