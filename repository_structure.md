JARVIS GitHub Repository Structure

For this 48-hour hackathon, we are using a Monorepo approach. This keeps all system components (Frontend, Backend, Hardware, and Math Simulations) in one place, ensuring no one gets out of sync and making the judges' code review much easier.

Directory Tree

jarvis-swarm/
â”œâ”€â”€ base_station/              # BACKEND (Python) - Hosted on Jetson Orin
â”‚   â”œâ”€â”€ api/                   # FastAPI routes, WebSockets
â”‚   â”‚   â””â”€â”€ main.py            # App entry point
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ ai_bridge.py       # Ollama JSON parsing & ElevenLabs TTS
â”‚   â”‚   â”œâ”€â”€ swarm_logic.py     # NetworkX Gossip protocol graph logic
â”‚   â”‚   â””â”€â”€ mqtt_client.py     # Mosquitto MQTT publisher/subscriber
â”‚   â”œâ”€â”€ requirements.txt       # Python dependencies
â”‚   â””â”€â”€ .env           # Local-only secrets, never commit
â”‚
â”œâ”€â”€ command_center/            # FRONTEND (React / Vite) - The UI
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ components/        # UI Widgets (Push-to-Talk button, status panels)
â”‚   â”‚   â”œâ”€â”€ graph/             # `react-force-graph` implementation
â”‚   â”‚   â””â”€â”€ hooks/             # WebSocket/Socket.io listener hooks
â”‚   â”œâ”€â”€ package.json
â”‚   â”œâ”€â”€ vite.config.js
â”‚   â””â”€â”€ tailwind.config.js
â”‚
â”œâ”€â”€ hardware/                  # EDGE HARDWARE (C++ / Arduino)
â”‚   â”œâ”€â”€ gateway_node/          # ESP32-1: Listens to MQTT over WiFi, sends ESP-NOW
â”‚   â”‚   â””â”€â”€ gateway_node.ino
â”‚   â””â”€â”€ field_node/            # ESP32-2 & 3: Listens to ESP-NOW, toggles LEDs
â”‚       â””â”€â”€ field_node.ino
â”‚
â”œâ”€â”€ simulations/               # MATH & BENCHMARKS (Python)
â”‚   â”œâ”€â”€ tcp_vs_gossip.py       # Speed-up comparison logic
â”‚   â””â”€â”€ outputs/               # Auto-generated Matplotlib charts for the pitch deck
â”‚
â”œâ”€â”€ docs/                      # PITCH & DESIGN
â”‚   â”œâ”€â”€ mission_canvas.md      # H4D Dual-Use Business Logic
â”‚   â””â”€â”€ architecture.png       # Graph of how JARVIS works
â”‚
â”œâ”€â”€ .gitignore                 # MUST include: node_modules, .env, __pycache__, venv
â””â”€â”€ README.md                  # Instructions on how to run the physical demo


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
