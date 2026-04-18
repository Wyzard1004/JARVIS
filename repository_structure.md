JARVIS GitHub Repository Structure

For this 48-hour hackathon, we are using a Monorepo approach. This keeps all system components (Frontend, Backend, Hardware, and Math Simulations) in one place, ensuring no one gets out of sync and making the judges' code review much easier.

Directory Tree

jarvis-swarm/
├── base_station/              # BACKEND (Python) - Hosted on Jetson Orin
│   ├── api/                   # FastAPI routes, WebSockets
│   │   └── main.py            # App entry point
│   ├── core/
│   │   ├── ai_bridge.py       # Ollama JSON parsing & ElevenLabs TTS
│   │   ├── swarm_logic.py     # NetworkX Gossip protocol graph logic
│   │   └── mqtt_client.py     # Mosquitto MQTT publisher/subscriber
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Keep ElevenLabs API keys out of commits!
│
├── command_center/            # FRONTEND (React / Vite) - The UI
│   ├── src/
│   │   ├── components/        # UI Widgets (Push-to-Talk button, status panels)
│   │   ├── graph/             # `react-force-graph` implementation
│   │   └── hooks/             # WebSocket/Socket.io listener hooks
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── hardware/                  # EDGE HARDWARE (C++ / Arduino)
│   ├── gateway_node/          # ESP32-1: Listens to MQTT over WiFi, sends ESP-NOW
│   │   └── gateway_node.ino
│   └── field_node/            # ESP32-2 & 3: Listens to ESP-NOW, toggles LEDs
│       └── field_node.ino
│
├── simulations/               # MATH & BENCHMARKS (Python)
│   ├── tcp_vs_gossip.py       # Speed-up comparison logic
│   └── outputs/               # Auto-generated Matplotlib charts for the pitch deck
│
├── docs/                      # PITCH & DESIGN
│   ├── mission_canvas.md      # H4D Dual-Use Business Logic
│   └── architecture.png       # Graph of how JARVIS works
│
├── .gitignore                 # MUST include: node_modules, .env, __pycache__, venv
└── README.md                  # Instructions on how to run the physical demo


Separation of Concerns (Why this works for us)

This structure is designed specifically so the four of you don't run into merge conflicts at 3:00 AM.

William: Owns command_center/ and base_station/api/. You control the visual layer and the routing.

Richard: Lives entirely in base_station/core/ai_bridge.py. He can write and test his LLM/Audio script completely isolated from the web server.

Giulia: Lives in base_station/core/swarm_logic.py. She just takes inputs and returns JSON.

Sebastian: Lives in simulations/ and helps William map the hardware/ scripts to the Jetson Orin.

Hackathon Git Workflow Rules

Main Branch is Sacred: The main branch MUST always be in a runnable state. If a judge pulls it, it should work.

Folder-Based Branches: Since you are working in isolated folders, name your branches by your folder/feature.

git checkout -b frontend-graph-ui

git checkout -b backend-gossip-logic

git checkout -b hardware-esp-now

The .env Rule: Whoever sets up the repo first MUST create the .gitignore immediately to prevent .env files (containing OpenAI or ElevenLabs API keys) from being pushed to GitHub.

The "Wow Factor" README

The README.md at the root of this repo needs to be treated as part of the pitch. Judges will scan it. It should include:

High-Level Pitch: What JARVIS is.

Architecture Diagram: Showing the Jetson -> ESP32 -> React flow.

Benchmark Results: Sebastian's Math output showing why Gossip is better than TCP in DDIL environments.

Hardware Requirements: A flex list showing what physical hardware this code is currently running on across the table.