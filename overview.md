JARVIS Master Blueprint

Project Name: JARVIS (Joint Adaptive Resilient Voice Integrated Swarm)
Hackathon: Critical Ops Hackathon (April 2026)

1. Target Problem Statements

Primary: Problem 10 (Swarm Coordination Protocol for Contested Environments)

"Build a multi-agent simulation in which a team of drones must collaboratively search a defined area and report objects of interest back to a base station — while maintaining coordination even when individual agents lose communication intermittently. Implement and compare at least two swarm consensus algorithms. All results should be visualized and benchmarked."

Secondary: Problem 16 (Edge Inference)

"Optimize and deploy Meta’s open-source AI models... for real-time edge inference on resource-constrained hardware, delivering state-of-the-art AI capabilities where cloud connectivity cannot be assumed... in disconnected, denied, or intermittent (DDIL) environments."

2. Project Overview & Mission

JARVIS is a voice-activated, hardware-in-the-loop swarm coordination system designed for DDIL environments.

Instead of a human operator micromanaging drone flight paths via a tablet, the operator acts as a node in a decentralized "Gossip Protocol" network. The human speaks naturally; a local edge-deployed LLM translates the speech into strict JSON commands; and the swarm executes the coordination logic using a resilient, leaderless graph network.

The Hackathon "Wow" Factor: The core logic runs entirely offline on an Nvidia Jetson Orin (Base Station), and commands are visualized both on a React graph and physically on ESP32 microcontrollers. This directly answers both Problem 10's simulation requirements and Problem 16's edge hardware requirements.

3. System Architecture & Tech Stack

A. Hardware Layer

Nvidia Jetson Orin: The central edge compute node. Hosts the LLM, the FastAPI backend, and the MQTT Broker.

ESP32 Microcontrollers: Physical representations of the swarm drones. They listen to MQTT and light up LEDs to demonstrate the Gossip protocol propagating through the network.

B. The AI / Voice Pipeline

Input (STT): OpenAI Whisper (or local whisper.cpp).

Logic (LLM): Ollama running a quantized Llama-3-8B-Instruct (Hosted on the Jetson Orin).

Output (TTS): ElevenLabs Python API (Generates JARVIS confirmation voice).

C. The Backend & Comm Layer

API: Python FastAPI (Serves the UI, handles routing).

Graph Logic: Python NetworkX (Calculates Gossip protocol propagation, routing, and swarm state).

Swarm Messaging: Mosquitto MQTT Broker (paho-mqtt in Python).

D. The Frontend (Command Center)

Framework: React + Vite + Tailwind CSS.

Visualization: react-force-graph (2D or 3D WebGL) for real-time node simulation.

Sync: WebSockets (Socket.io or FastAPI WebSockets) linking the React UI to the Python backend.

4. The Live Demo Flow (Step-by-Step)

Command: User presses a hotkey on the React UI and speaks: "JARVIS, re-route swarm to Grid Alpha."

Translation: Audio is transcribed. Local Llama 3 parses the text and outputs strict JSON.

Confirmation: ElevenLabs generates audio: "Re-routing swarm to Grid Alpha."

Graph Execution: Giulia's NetworkX logic calculates the gossip propagation path.

Hardware Sync: FastAPI pushes staggered messages to the MQTT broker. The physical ESP32s light up sequentially.

Visual Sync: FastAPI pushes WebSocket updates to React. The nodes on the force-graph turn red and physically cluster around coordinates representing "Grid Alpha."

5. API & Data Contracts (Crucial for Dev)

Llama 3 Output Expected JSON:

{
  "intent": "swarm_redeploy",
  "target_location": "Grid Alpha",
  "action_code": "RED_ALERT",
  "confidence": 0.95
}


WebSocket Payload (Backend -> React UI):

{
  "event": "gossip_update",
  "active_nodes": ["node_1", "node_2", "node_5"],
  "target_x": 150,
  "target_y": -50,
  "status": "swarming"
}
