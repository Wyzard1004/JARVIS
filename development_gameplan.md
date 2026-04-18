JARVIS Execution Gameplan

System: Joint Adaptive Resilient Voice Integrated Swarm
Phase Structure: [X.Y.Z]

X = Separable Technology Track (Assignee)

Y = Major Milestone / Component

Z = Minor Execution Task

1.0.0 Hardware & Edge Infrastructure (Assignee: Sebastian)

Focus: Establishing the offline Base Station and the ESP32 direct-radio swarm network.

1.1 Jetson Orin Base Station Setup

1.1.1: Connect Jetson Orin to the local network and establish stable SSH access for the team.

1.1.2: Install Ollama and pull the quantized llama3 (or llama-3-8b-instruct) model. Verify local inference via CLI.

1.1.3: Install and configure Mosquitto MQTT broker to accept local connections from the FastAPI backend and Gateway ESP32.

1.2 ESP32 Radio Swarm Network

Context: We have 3 ESP32s. 1 Gateway, 2 Field Drones. They will communicate via ESP-NOW (direct peer-to-peer radio, no Wi-Fi router needed).

1.2.1: Program ESP32-1 (Gateway). Connect it to the Jetson via serial/USB or local MQTT. Program it to receive commands from the backend and broadcast them via ESP-NOW radio.

1.2.2: Program ESP32-2 & ESP32-3 (Field Drones). Set them to listen for ESP-NOW radio packets. Program LED logic to flash Red upon receiving an ACTION payload.

1.2.3: Implement simulated "Gossip" propagation. Add a slight, randomized artificial delay (100ms - 400ms) on ESP32-2 and ESP32-3 so they don't light up simultaneously, visually proving the multi-hop transmission concept.

2.0.0 Graph Algorithm & Math Logic (Assignee: Giulia)

Focus: The "Brain" of the swarm, calculating paths and benchmarking Gossip vs. TCP.

2.1 Swarm State & Gossip Logic (NetworkX)

2.1.1: Initialize the base NetworkX graph representing the operational space and drone nodes.

2.1.2: Write the Gossip propagation algorithm. Given a target (e.g., [x: 150, y: -50]), calculate the exact order and simulated timestamp each drone node receives the command.

2.1.3: Format the output. Write a function that returns the calculated state as a strict JSON array of nodes, edges, and statuses, ready for the UI to consume.

2.2 Benchmarking & Math Validation (Prompt Requirement)

2.2.1: Implement a baseline "TCP/Raft" simulation model to compare against our Gossip protocol.

2.2.2: Calculate the math: Quantify the bandwidth saved and latency reduced by Gossip in a partitioned network scenario.

2.2.3: Generate a visual output (Matplotlib chart or simple JSON stats) of the benchmark so Richard can put it directly into the final pitch deck.

3.0.0 AI Pipeline Bridge (Assignee: Richard)

Focus: Wrapping the Voice & LLM layers into a clean, testable Python module.

3.1 LLM Intent Parsing

3.1.1: Write a Python function using requests to ping the local Ollama API (localhost:11434).

3.1.2: Prompt Engineer the LLM to act as a strict JSON-schema extractor. It must take a string ("Swarm, push to Grid Alpha") and output exactly: {"intent": "swarm", "target": "Grid Alpha", "action": "RED_ALERT"}.

3.1.3: Implement error-handling. If the LLM hallucinates non-JSON text, automatically retry or default to a safe fallback state.

3.2 Voice Synthesis & Audio Polish

3.2.1: Set up the ElevenLabs Python SDK with the correct API keys.

3.2.2: Write a function that accepts a confirmation string (e.g., "Targets acquired.") and generates an output.mp3.

3.2.3: Package the entire flow into ai_bridge.py. Expose a single function: process_voice_command(transcribed_text) that handles the LLM parsing and triggers the ElevenLabs audio.

4.0.0 Full-Stack Integration & Command UI (Assignee: William)

Focus: Stitching the pipelines together and building the visual "Wow" factor.

4.1 The FastAPI Hub (Nervous System)

4.1.1: Scaffold a FastAPI application on the Jetson Orin. Import ai_bridge.py (Richard) and swarm_logic.py (Giulia).

4.1.2: Integrate paho-mqtt. Set up the Python server to publish commands to the Gateway ESP32 when an LLM intent is triggered.

4.1.3: Set up a WebSocket endpoint (/ws/swarm) to blast real-time state updates to the React frontend.

4.2 React Command Center (The Dashboard)

4.2.1: Initialize the Vite + React app. Implement a dark-mode, high-contrast Tailwind layout.

4.2.2: Integrate react-force-graph. Map the incoming WebSocket data to the nodes/links props.

4.2.3: Build the user interaction layer: Add a "Push to Talk" button on the UI that captures microphone audio, sends it to Whisper for transcription, and fires it to the FastAPI backend.

4.3 The "Smoke & Mirrors" Sync (Final Polish)

4.3.1: Write the UI animations. When the WebSocket receives a "swarming" status, dynamically update the D3 center-force to pull all active drone nodes to the targeted X/Y coordinate.

4.3.2: Coordinate the timing. Ensure the UI graph pulses Red at the exact same time the physical ESP-NOW field drones light up their LEDs.