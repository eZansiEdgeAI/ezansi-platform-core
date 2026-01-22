# ezansi-platform-core: Copilot Agent Instructions

## Repository Overview

**What it does:** This is the routing + discovery "hub" for the eZansi Edge AI platform. It's a minimal FastAPI gateway that discovers AI capabilities (LLM, retrieval, TTS, STT, vision, etc.) via `capability.json` contracts, validates resource requirements, routes requests by service type, and provides a stable platform API for experience layers.

**Key characteristics:**
- **Size:** Small codebase (~10 Python files, 54MB total, 2088 files including .git)
- **Type:** Platform infrastructure / API gateway
- **Language:** Python 3.11+ (tested on 3.12.3)
- **Framework:** FastAPI 0.115.6, httpx 0.27.2, Pydantic 2.10.4, uvicorn 0.30.6
- **Runtime:** Containerized with Podman (version 4.9.3), orchestrated via podman-compose 1.5.0
- **Architecture:** Three-layer LEGO brick model - Platform Core (this repo) orchestrates independent Capability containers

## Project Structure

```
ezansi-platform-core/
├── src/ezansi_platform_core/     # Main application code
│   ├── __init__.py               # Version: 0.1.0
│   ├── __main__.py               # Entry point (runs uvicorn server)
│   ├── app.py                    # FastAPI app with all endpoints
│   ├── contracts.py              # Pydantic models for contracts
│   ├── overrides.py              # Endpoint override logic
│   ├── registry.py               # Capability discovery/registry
│   ├── router.py                 # Request routing to capabilities
│   ├── settings.py               # Environment-based configuration
│   └── validator.py              # Resource validation
├── config/
│   ├── device-constraints.json   # Device resource limits
│   └── overrides.yaml            # Endpoint overrides for container networking
├── capabilities/                 # Demo capability contracts (mounted into container)
│   ├── ollama-llm/capability.json
│   └── chromadb-retrieval/capability.json
├── scripts/
│   ├── smoke-test.sh             # Platform health + registry tests
│   └── health-check.sh           # Basic health verification
├── tools/ezansi-advisor/         # External blueprint advisor tool
│   ├── advisor.py                # Reads blueprints, checks health
│   ├── Containerfile
│   ├── Makefile
│   └── requirements.txt
├── docs/                         # Architecture documentation
│   ├── deployment-guide.md       # Platform deployment steps
│   └── phase-2-architecture/     # Design docs
├── Containerfile                 # Container build definition
├── podman-compose.yml            # Container orchestration
├── requirements.txt              # Python dependencies
├── README.md                     # Primary documentation
├── REPOSITORY_SUMMARY.md         # Architecture summary
└── .gitignore                    # Excludes .venv/, __pycache__/, etc.
```

## Build, Run, and Test Instructions

### Environment Setup

**ALWAYS start with a clean Python virtual environment:**

```bash
# Create venv (one time)
python3 -m venv .venv

# Activate venv (required for every session)
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected time:** ~30 seconds for pip install on first run.

**Common issue:** If you see "ModuleNotFoundError", you forgot to activate the venv or set PYTHONPATH. Always run `source .venv/bin/activate` before any Python commands.

### Running the Platform Locally (Development)

**Critical:** Set `PYTHONPATH=src` to allow Python to find the `ezansi_platform_core` module.

```bash
# Start the server
source .venv/bin/activate
PYTHONPATH=src python -m ezansi_platform_core

# Or with custom settings
PYTHONPATH=src REGISTRY_PATH=./capabilities PORT=8000 python -m ezansi_platform_core
```

**Expected output:**
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Common issue:** "Address already in use" on port 8000. Kill the process: `lsof -ti:8000 | xargs kill -9` and retry.

### Testing the Platform

**Always run these health checks after any code changes:**

```bash
# Basic health check (platform is alive)
curl -fsS http://localhost:8000/health

# Platform info (version, capability count)
curl -fsS http://localhost:8000/info

# List discovered capabilities
curl -fsS http://localhost:8000/registry

# Comprehensive smoke test
PLATFORM_BASE_URL=http://localhost:8000 bash scripts/smoke-test.sh
```

**Expected results:**
- `/health` returns `{"status":"healthy","uptime_s":N}`
- `/info` returns platform version 0.1.0 and capabilities_count
- `/registry` returns array of capability objects (may be empty if no capabilities mounted)

### Container Build and Run

**Note:** Container builds require network access and may fail in restricted environments. Use `sudo` with podman if permission errors occur.

```bash
# Build the container (expected time: 2-3 minutes on first run)
sudo podman build -t localhost/ezansi-platform-core:latest -f Containerfile .

# Run with podman-compose (creates network, volumes, mounts ./capabilities)
podman-compose up -d

# Verify running containers
podman ps

# View logs
podman logs ezansi-platform-core

# Stop containers (use -t 10 for graceful shutdown timeout)
podman-compose down
# OR
podman stop -t 10 ezansi-platform-core
```

**Important:** The first `podman-compose up -d` creates containers with names and networking. After that, use `podman start ezansi-platform-core` or `podman-compose up -d` to restart existing containers.

**Container environment variables** (set in podman-compose.yml):
- `PORT`: Server port (default 8000)
- `REGISTRY_PATH`: Where to scan for capability.json files (default /capabilities)
- `CONSTRAINTS_PATH`: Device constraints file (default /app/config/device-constraints.json)
- `OVERRIDES_PATH`: Endpoint override config (default /app/config/overrides.yaml)
- `CACHE_TTL_SECONDS`: Registry cache duration (default 10)
- `STRICT_MODE`: Resource validation strictness (default true)
- `HTTP_TIMEOUT_SECONDS`: HTTP request timeout (default 30)

### Validation Scripts

**Use the provided scripts for quick validation:**

```bash
# Quick health check (3 endpoints)
bash scripts/health-check.sh

# Comprehensive smoke test (health, registry, status, stack validation)
PLATFORM_BASE_URL=http://localhost:8000 bash scripts/smoke-test.sh
```

## Development Workflow

### Making Code Changes

1. **Always activate venv first:** `source .venv/bin/activate`
2. **Set PYTHONPATH:** `export PYTHONPATH=src` (or prefix commands with it)
3. **Make targeted changes** to files in `src/ezansi_platform_core/`
4. **Test immediately** with local server run
5. **Verify health endpoints** return expected responses

### Common Development Tasks

**Adding a new endpoint to the platform:**
- Edit `src/ezansi_platform_core/app.py`
- Follow existing FastAPI route patterns
- Test with `curl` commands immediately

**Modifying capability discovery logic:**
- Edit `src/ezansi_platform_core/registry.py`
- Restart server to reload registry logic
- Verify with `curl http://localhost:8000/registry`

**Changing routing behavior:**
- Edit `src/ezansi_platform_core/router.py`
- Test with actual capability contract or mock endpoint

**Updating resource validation:**
- Edit `src/ezansi_platform_core/validator.py`
- Test with `curl -X POST http://localhost:8000/validate/stack`

### Configuration Files

**Do NOT modify these without understanding their purpose:**

- `config/device-constraints.json`: Defines available device resources (CPU, RAM, storage)
- `config/overrides.yaml`: Maps localhost endpoints to container-accessible URLs
- `podman-compose.yml`: Container orchestration configuration
- `Containerfile`: Container image build steps

**When you need to test with different constraints:** Temporarily modify `config/device-constraints.json` but document your changes.

## Testing and Validation

### No formal test suite
This repository **does not have pytest or unit tests**. Validation relies on:
1. Running the server and checking logs for startup errors
2. Calling HTTP endpoints and verifying responses
3. Using provided scripts: `scripts/health-check.sh` and `scripts/smoke-test.sh`

### Manual Testing Checklist

After making changes, always:
- [ ] Activate venv and set PYTHONPATH
- [ ] Start the server without errors
- [ ] Verify `/health` returns 200 OK
- [ ] Verify `/info` returns correct version
- [ ] Verify `/registry` returns valid JSON (array)
- [ ] If capability contracts are mounted, verify they appear in registry
- [ ] Stop the server cleanly (Ctrl+C or kill)

### Container Testing

If modifying Containerfile or podman-compose.yml:
- [ ] Build container successfully with `sudo podman build`
- [ ] Start with `podman-compose up -d`
- [ ] Check logs: `podman logs ezansi-platform-core`
- [ ] Verify health endpoint from host: `curl localhost:8000/health`
- [ ] Stop cleanly: `podman-compose down`

## Common Pitfalls and Solutions

### Python Module Not Found
**Symptom:** `ModuleNotFoundError: No module named 'ezansi_platform_core'`  
**Solution:** Set `PYTHONPATH=src` before running Python commands, or use `PYTHONPATH=src python -m ezansi_platform_core`

### Port Already in Use
**Symptom:** `error while attempting to bind on address ('0.0.0.0', 8000): address already in use`  
**Solution:** Kill the existing process: `lsof -ti:8000 | xargs kill -9`, then retry

### Empty Registry
**Symptom:** `/registry` returns `[]` even though capabilities exist  
**Solution:** Verify `REGISTRY_PATH` environment variable points to correct directory (default is `/capabilities` in container, `./capabilities` for local dev). Ensure capability.json files exist in subdirectories.

### Container Build Permission Errors
**Symptom:** `Permission denied` or `Interactive authentication required` during `podman build`  
**Solution:** Use `sudo podman build` instead of `podman build`

### Dependencies Not Found
**Symptom:** `ImportError` for fastapi, httpx, pydantic, etc.  
**Solution:** You forgot to install dependencies. Run `pip install -r requirements.txt` in activated venv

## Architecture Details

### Request Flow
1. Client sends `POST /` with `{type: "text-generation", payload: {...}}`
2. Registry resolves service type → capability provider (e.g., "ollama-llm")
3. Router checks provider health via `api.health_check` endpoint
4. Router forwards request to provider endpoint using httpx
5. Platform returns normalized response: `{status, type, data, metadata}`

### Capability Contract Schema
Capabilities advertise themselves via `capability.json` files:
```json
{
  "name": "ollama-llm",
  "version": "1.0",
  "provides": ["text-generation"],
  "api": {
    "endpoint": "http://localhost:11434",
    "health_check": "/api/tags"
  },
  "endpoints": {
    "generate": {"method": "POST", "path": "/api/generate"}
  },
  "resources": {"ram_mb": 6000, "cpu_cores": 4}
}
```

**Registry scans** `REGISTRY_PATH` for `**/capability.json` files on startup and caches results for `CACHE_TTL_SECONDS`.

### Endpoint Overrides
The `config/overrides.yaml` file rewrites capability endpoints for container networking:
- Capability contract uses `http://localhost:11434`
- Override maps it to `http://host.containers.internal:11434` for container access
- This allows capabilities to run on host while platform runs in container

## Key Constraints and Guidelines

### When to Update Platform-Core
**Do update when:**
- Multiple capabilities reveal a common platform need
- Contract specification needs refinement
- Platform bugs discovered
- New composition patterns emerge

**Do NOT update when:**
- Adding new capabilities (they should work with existing platform)
- Building capability-specific features (stay in capability repo)

### Code Style
- No formal linter configured (no .pylintrc, .flake8, etc.)
- Follow existing code patterns in the codebase
- Use type hints (`from __future__ import annotations`)
- Keep modules small and focused (current files are 50-200 lines)

### Dependencies
- **Minimize new dependencies.** This is a stable platform foundation.
- Only add libraries if absolutely necessary for platform functionality
- Keep requirements.txt minimal (currently just 5 core packages)

## External Tools and Repos

### ezansi-advisor (in tools/)
- **Purpose:** External CLI/container that reads blueprints and checks platform health
- **Build:** `cd tools/ezansi-advisor && make build TAG=0.1.2`
- **Not part of platform runtime** - this is an auxiliary development tool

### Related Repositories
- **ezansi-capability-llm-ollama:** LLM capability (Ollama wrapper)
- **ezansi-capability-retrieval-chromadb:** Vector search capability
- **ezansi-blueprints:** Stack composition blueprints (separate repo)

## Quick Reference Commands

```bash
# Setup (one time)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run locally (every time)
source .venv/bin/activate
PYTHONPATH=src python -m ezansi_platform_core

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/registry
bash scripts/smoke-test.sh

# Container workflow
sudo podman build -t localhost/ezansi-platform-core:latest -f Containerfile .
podman-compose up -d
podman logs ezansi-platform-core
podman-compose down

# Cleanup
deactivate  # Exit venv
lsof -ti:8000 | xargs kill -9  # Kill server if stuck
```

## Trust These Instructions

**This file was created by thoroughly exploring and testing the codebase.** When working on this repository:
- **Trust these build/run steps** - they have been validated
- Only search for additional information if these instructions are incomplete or incorrect
- Report discrepancies if you find the instructions are outdated

**Last validated:** 2026-01-22 with Python 3.12.3, Podman 4.9.3, podman-compose 1.5.0
