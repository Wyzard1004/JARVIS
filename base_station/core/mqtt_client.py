"""
JARVIS MQTT Client (Section 1.1.3 & 4.1.2)

Publishes gossip protocol results to Mosquitto MQTT broker.
Receives acknowledgments from ESP32 Gateway node.

Broker topology:
- Base Station (publisher): Publishes to swarm/command
- Gateway ESP32 (subscriber): Listens for commands via ESP-NOW
- Field Nodes (subscribers): Receive via ESP-NOW relay from Gateway
"""

import paho.mqtt.client as mqtt
import json
import asyncio
from typing import Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """
    Client for publishing gossip results to Mosquitto MQTT broker.
    
    Topics:
    - swarm/command: Outgoing commands to ESP32 nodes
    - swarm/status: Incoming status from ESP32s
    - swarm/telemetry: Sensor data from field nodes (future)
    """
    
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "jarvis_base_station"
    ):
        """
        Initialize MQTT client connection.
        
        Args:
            broker_host: Address of Mosquitto broker (default: localhost)
            broker_port: Port of Mosquitto broker (default: 1883)
            client_id: Client ID for MQTT identification
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.is_connected = False
        self.message_handlers: Dict[str, Callable] = {}
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT connects"""
        if rc == 0:
            self.is_connected = True
            logger.info(f"[MQTT] Connected to broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to status topics
            self.client.subscribe("swarm/status")
            self.client.subscribe("swarm/telemetry")
            print("[MQTT] Subscribed to swarm status topics")
        else:
            logger.error(f"[MQTT] Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when MQTT disconnects"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"[MQTT] Unexpected disconnection (code: {rc})")
        else:
            logger.info("[MQTT] Disconnected from broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        topic = msg.topic
        payload = msg.payload.decode()
        
        logger.debug(f"[MQTT] Received on {topic}: {payload}")
        
        # Route to registered handler if exists
        if topic in self.message_handlers:
            try:
                handler = self.message_handlers[topic]
                data = json.loads(payload)
                handler(data)
            except Exception as e:
                logger.error(f"[MQTT] Error processing message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"[MQTT] Message {mid} published")
    
    async def connect_async(self) -> bool:
        """
        Asynchronously connect to MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()  # Start background thread for network loop
            
            # Wait for connection to establish
            await asyncio.sleep(1)
            
            if self.is_connected:
                logger.info("[MQTT] Successfully connected to broker")
                return True
            else:
                logger.error("[MQTT] Failed to connect to broker")
                return False
        except Exception as e:
            logger.error(f"[MQTT] Connection error: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Synchronously connect to MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()  # Start background thread for network loop
            
            # Give it a moment to connect
            import time
            time.sleep(0.5)
            
            if self.is_connected:
                logger.info("[MQTT] Successfully connected to broker")
                return True
            else:
                logger.warning("[MQTT] Connection initiated, may still be connecting...")
                return True
        except Exception as e:
            logger.error(f"[MQTT] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("[MQTT] Disconnected from broker")
        except Exception as e:
            logger.error(f"[MQTT] Disconnection error: {e}")
    
    def publish_gossip_command(self, gossip_result: Dict) -> bool:
        """
        Publish a gossip protocol result to ESP32s.
        
        Args:
            gossip_result: Output from swarm_logic.calculate_gossip_path()
        
        Returns:
            True if publish successful
        """
        try:
            payload = json.dumps(gossip_result)
            result = self.client.publish(
                topic="swarm/command",
                payload=payload,
                qos=1  # QoS 1: At least once delivery
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"[MQTT] Published gossip command to swarm/command")
                return True
            else:
                logger.error(f"[MQTT] Publish failed with code {result.rc}")
                return False
        except Exception as e:
            logger.error(f"[MQTT] Error publishing gossip command: {e}")
            return False
    
    def publish_status_request(self, node_id: str) -> bool:
        """
        Request status from a specific node.
        
        Args:
            node_id: Node identifier (e.g., "gateway", "field-1")
        
        Returns:
            True if publish successful
        """
        try:
            payload = json.dumps({"node": node_id, "request": "status"})
            result = self.client.publish(
                topic=f"swarm/nodes/{node_id}/status",
                payload=payload,
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"[MQTT] Requested status from {node_id}")
                return True
            else:
                logger.error(f"[MQTT] Status request failed with code {result.rc}")
                return False
        except Exception as e:
            logger.error(f"[MQTT] Error requesting status: {e}")
            return False
    
    def register_message_handler(self, topic: str, callback: Callable):
        """
        Register a callback function for incoming messages on a topic.
        
        Args:
            topic: MQTT topic to listen to
            callback: Function to call when message received
        """
        self.message_handlers[topic] = callback
        self.client.subscribe(topic)
        logger.info(f"[MQTT] Registered handler for {topic}")
    
    def publish_raw(self, topic: str, payload: Dict) -> bool:
        """
        Publish a raw JSON payload to a topic.
        
        Args:
            topic: MQTT topic
            payload: Dictionary to publish as JSON
        
        Returns:
            True if publish successful
        """
        try:
            result = self.client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"[MQTT] Published to {topic}")
                return True
            else:
                logger.error(f"[MQTT] Publish to {topic} failed with code {result.rc}")
                return False
        except Exception as e:
            logger.error(f"[MQTT] Error publishing to {topic}: {e}")
            return False


# Global MQTT instance
_mqtt_publisher: Optional[MQTTPublisher] = None


def get_mqtt_publisher(
    broker_host: str = "localhost",
    broker_port: int = 1883
) -> MQTTPublisher:
    """
    Get or create global MQTT publisher instance.
    
    Args:
        broker_host: Address of Mosquitto broker
        broker_port: Port of Mosquitto broker
    
    Returns:
        MQTTPublisher instance
    """
    global _mqtt_publisher
    
    if _mqtt_publisher is None:
        _mqtt_publisher = MQTTPublisher(broker_host, broker_port)
    
    return _mqtt_publisher
