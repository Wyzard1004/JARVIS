# JARVIS Docs

This folder is the active documentation set for JARVIS: Joint Autonomous Recon and Vision Integrated Swarm.

These files are written to match the live codebase, especially:

- the FastAPI base station in [../base_station/api/main.py](../base_station/api/main.py)
- the Jetson relay bridge in [../base_station/headless/serial_ptt_listener.py](../base_station/headless/serial_ptt_listener.py)
- the React command center in [../command_center/src/App.jsx](../command_center/src/App.jsx)
- the ESP32 relay firmware in [../hardware/gateway_node/src/main.cpp](../hardware/gateway_node/src/main.cpp) and [../hardware/field_node/src/main.cpp](../hardware/field_node/src/main.cpp)

## Start Here

- [OVERVIEW.md](OVERVIEW.md): current system shape, deployment story, and code-backed architecture
- [SETUP.md](SETUP.md): local laptop plus Jetson setup for the current stack
- [TESTING.md](TESTING.md): smoke tests for backend, frontend, Jetson PTT, and ESP32 relay flow
- [COMMAND_SCHEMA.md](COMMAND_SCHEMA.md): current parser contract and command lifecycle
- [EXAMPLES.md](EXAMPLES.md): realistic operator phrases that match the parser today
- [ROADMAP.md](ROADMAP.md): what is shipped, what is next, and what is still aspirational
- [CHANGE_PROPOSAL.md](CHANGE_PROPOSAL.md): near-term improvements grounded in the current architecture
- [SOURCES.md](SOURCES.md): public-source rationale for terminology, control flow, and operator phrasing

## Reading Order For GitHub Visitors

If you only read three files, use:

1. [../README.md](../README.md)
2. [OVERVIEW.md](OVERVIEW.md)
3. [SETUP.md](SETUP.md)

## Historical Notes

Older phase writeups, quickstarts, and handoff notes live in `docs/archive/`.

They are useful for history, but they may still describe:

- MQTT as the hardware transport plan
- older UI structures
- pre-relay-hardware assumptions
- superseded naming

Treat the files in this folder as the current source of truth instead.
