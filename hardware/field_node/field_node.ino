#include <esp_now.h>
#include <WiFi.h>

// Define your LED pin (Internal LED is usually 2, or use an external pin)
const int LED_PIN = 2; 

// State variables for the non-blocking 5-second timer
bool isSwarming = false;
unsigned long swarmStartTime = 0;
const unsigned long SWARM_DURATION = 5000; // 5 seconds

// Structure to receive data (Must match the sender!)
typedef struct struct_message {
  char command[16];
} struct_message;

struct_message incomingData;

// Callback function that fires the millisecond a radio wave hits the antenna
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingDataBytes, int len) {
  memcpy(&incomingData, incomingDataBytes, sizeof(incomingData));
  
  // If the Gateway sent the SWARM command
  if (strcmp(incomingData.command, "SWARM") == 0) {
    digitalWrite(LED_PIN, HIGH);   // Instantly turn on LED
    isSwarming = true;             // Trigger the timer state
    swarmStartTime = millis();     // Record the exact time it started
    
    // Optional: Send an ACK back here via Serial if this was plugged into a PC
    Serial.println("Command received: Executing Swarm.");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Set device as a Wi-Fi Station (Required for ESP-NOW)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(); // Disconnect from any routers to ensure clean radio

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  
  // Register the receive callback function
  esp_now_register_recv_cb(OnDataRecv);
  Serial.println("Drone Node Ready. Waiting for JARVIS commands...");
}

void loop() {
  // Non-blocking timer check
  if (isSwarming) {
    if (millis() - swarmStartTime >= SWARM_DURATION) {
      digitalWrite(LED_PIN, LOW); // Turn off LED
      isSwarming = false;         // Reset state
      Serial.println("Swarm action complete. Returning to standby.");
    }
  }
  // The loop runs lightning fast because there are no delay() functions
}