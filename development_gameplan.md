JARVIS Execution Gameplan

System: Joint Adaptive Relay for Variable Interoperable Swarms
Phase Structure: [X.Y.Z]

X = Separable Technology Track (Assignee)

Y = Major Milestone / Component

Z = Minor Execution Task

1.0.0 Hardware and Edge Infrastructure (Assignee: Sebastian)

Focus: Establishing the offline Base Station and the ESP32 relay path for the physical demo.

1.1 Jetson Orin Base Station Setup

1.1.1: [ ] Connect Jetson Orin to the local network and establish stable SSH access for the team.

1.1.2: [ ] Install Ollama and pull the quantized model used for local command normalization.

1.1.3: [ ] Install and configure Mosquitto MQTT broker for local communication between the backend and gateway ESP32.

1.2 ESP32 Relay Network

Context: We have a gateway node plus field nodes. They should demonstrate contested-environment message relay and staged propagation.

1.2.1: [ ] Program ESP32 Gateway to receive commands from the backend and rebroadcast them over ESP-NOW or equivalent field link.

1.2.2: [ ] Program field nodes to listen for relay packets and show receipt with LED behavior or status reporting.

1.2.3: [ ] Add slight randomized delay and forwarding behavior so the physical demo visually reinforces multi-hop dissemination instead of simultaneous activation.

2.0.0 Consensus and Search Logic (Assignee: Giulia)

Focus: The swarm coordination core, including propagation, resilience, and benchmark output.

2.1 Swarm State and Consensus Runtime

2.1.1: [x] Initialize the operational graph representing relay, operator, recon, and attack nodes.

2.1.2: [x] Implement adaptive gossip propagation with retries, duplicate suppression, relay fanout, and disruption handling.

2.1.3: [x] Format the output as UI-ready JSON with nodes, edges, active nodes, propagation order, and mission state.

2.2 Benchmarking and Prompt Alignment

2.2.1: [x] Implement a leader-based TCP/Raft-style baseline for comparison against gossip.

2.2.2: [x] Quantify latency, bandwidth, and fault-tolerance tradeoffs under disrupted network conditions.

2.2.3: [ ] Add additional benchmark visual outputs or charts for the final pitch deck as needed.

2.3 Next Growth Areas

2.3.1: [ ] Expand the topology with more node roles, scenarios, and search/report behaviors.

2.3.2: [ ] Add richer contested-network events such as timed outages, degraded links, and reassignment behavior.

3.0.0 Command and Intent Bridge (Assignee: Richard)

Focus: Turning operator input into a safe, normalized swarm command object. Voice is optional; the command contract is primary.

3.1 Structured and Text Command Parsing

3.1.1: [x] Build a Python function that can normalize operator language into a safe JSON command shape.

3.1.2: [x] Support local Ollama as an optional parser behind a safe fallback path.

3.1.3: [x] Implement error handling and fallback behavior so the swarm path does not depend on perfect model output.

3.2 Optional Audio and Confirmation Layer

3.2.1: [x] Add speech-to-text helper support for microphone uploads when audio is used.

3.2.2: [x] Add confirmation text and optional TTS helper functions.

3.2.3: [ ] Keep audio and TTS non-blocking so direct structured commands remain the primary reliable control path.

3.3 Interface Stability

3.3.1: [ ] Lock the normalized command schema shared by direct payloads, AI parsing, and the swarm runtime.

3.3.2: [ ] Keep confidence, location normalization, and safe fallback behavior consistent across all input modes.

4.0.0 Full-Stack Integration and Command UI (Assignee: William)

Focus: Stitching the pipelines together and making the consensus behavior legible in the UI.

4.1 The FastAPI Hub

4.1.1: [x] Scaffold and run a FastAPI application that imports `ai_bridge.py` and `swarm_logic.py`.

4.1.2: [x] Dispatch swarm commands through either adaptive gossip or the TCP/Raft baseline based on request payloads.

4.1.3: [ ] Wire `mqtt_client.py` into the live dispatch path for hardware publishing.

4.1.4: [x] Expose a WebSocket endpoint (`/ws/swarm`) for real-time state updates to the frontend.

4.2 React Command Center

4.2.1: [x] Initialize the Vite + React app and ship a working command center shell.

4.2.2: [x] Render incoming WebSocket data in the swarm graph and status panel.

4.2.3: [ ] Make structured command controls first-class in the UI, with push-to-talk retained only as an optional demo input.

4.2.4: [x] Maintain command history and live connection state for operator visibility.

4.3 Final Polish

4.3.1: [x] Animate propagation and state changes in the graph so the consensus flow is visually obvious.

4.3.2: [ ] Synchronize UI timing with hardware timing once MQTT and ESP32 relay are wired end to end.

5.0.0 Narrative and Demo Readiness

Focus: Keeping the repo story aligned with what is actually implemented.

5.1 Documentation

5.1.1: [x] Reframe the project around swarm coordination and contested-environment consensus.

5.1.2: [x] Move voice from the identity of the project to an optional operator-interface layer in the docs.

5.1.3: [ ] Update pitch materials with the latest benchmark snapshots and topology screenshots before submission.
