# End-to-End Testing Guide (Manual + Automated)

This guide covers two things:

- **Manual end-to-end tests (Podman, cold start)**: what a new user can do from cloning repos to a working multi-container stack.
- **Automated tests (pytest)**: the test suite that runs in CI and locally.

If you only want the fastest confirmation that “it works”, start with the 5-minute happy path.

## 5-minute happy path (Podman)

This is the shortest “prove the system works” path.

Assumptions:

- You already have `podman`, `podman-compose`, and `curl` installed.
- You have the three repos cloned as sibling folders:
  - `ezansi-platform-core`
  - `ezansi-capability-llm-ollama`
  - `ezansi-capability-retrieval-chromadb`

Steps:

1. Start Ollama:
   ```bash
   cd ../ezansi-capability-llm-ollama
   podman-compose up -d
   ./scripts/pull-model.sh mistral
   ```

2. Start Retrieval (ChromaDB):
   ```bash
   cd ../ezansi-capability-retrieval-chromadb
   ./scripts/deploy.sh --profile pi5  # or: pi4, amd64 (or omit for defaults)
   ./scripts/validate-deployment.sh
   ```

3. Make capability contracts visible to the platform gateway:
   ```bash
   cd ../ezansi-platform-core
   mkdir -p capabilities/ollama-llm capabilities/chromadb-retrieval
   cp ../ezansi-capability-llm-ollama/capability.json capabilities/ollama-llm/capability.json
   cp ../ezansi-capability-retrieval-chromadb/capability.json capabilities/chromadb-retrieval/capability.json
   ```

4. Build + start the platform gateway (cold start safe):
   ```bash
   podman-compose up -d --build
   ```

5. Run the built-in smoke test:
   ```bash
   ./scripts/smoke-test.sh
   ```

6. Execute a real request through the gateway (LLM + retrieval):

   LLM (text-generation):
   ```bash
   curl -fsS -X POST http://localhost:8000/ \
     -H 'Content-Type: application/json' \
     -d '{"type":"text-generation","payload":{"endpoint":"generate","json":{"model":"mistral","prompt":"Hello from ezansi-platform-core","stream":false}}}'
   ```

   Retrieval (vector-search):
   ```bash
   curl -fsS -X POST http://localhost:8000/ \
     -H 'Content-Type: application/json' \
     -d '{"type":"vector-search","payload":{"endpoint":"ingest","params":{"collection":"demo"},"json":{"documents":[{"id":"doc1","text":"RAG is retrieval augmented generation.","metadata":{"source":"manual"}}]}}}'

   curl -fsS -X POST http://localhost:8000/ \
     -H 'Content-Type: application/json' \
     -d '{"type":"vector-search","payload":{"endpoint":"query","params":{"collection":"demo"},"json":{"query":"What is RAG?","top_k":3}}}'
   ```

### What “success” looks like

- `./scripts/smoke-test.sh` prints healthy `registry` and `status` output and `validate/stack` returns `{"ok":true,...}`.
- The LLM call returns JSON with a generated response.
- The retrieval query returns results with `matches` (top_k items).

## Absolute beginner: single cold-start path (from clone to working stack)

This is the full “new machine” path: install dependencies, build/pull images, run containers, validate.

### 0) Install prerequisites (Podman-only)

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y podman podman-compose curl
podman --version
podman-compose --version
```

Notes:

- First run requires internet access to pull base images and Python dependencies.
- Some distros require enabling rootless Podman services for the best experience.

### 1) Clone the repos

```bash
mkdir -p ~/Projects/ezansi
cd ~/Projects/ezansi

git clone https://github.com/eZansiEdgeAI/ezansi-platform-core.git
git clone https://github.com/eZansiEdgeAI/ezansi-capability-llm-ollama.git
git clone https://github.com/eZansiEdgeAI/ezansi-capability-retrieval-chromadb.git
```

Not part of this E2E flow:

- `ezansi-capability-tts-piper` (not integrated into the platform-core gateway E2E path yet)
- `capability-template` (placeholder/template for future capabilities)
- `ezansi-blueprints` (optional; used by advisor tooling, not deployed as a container)

### 2) Start the capabilities (pull/build)

Start Ollama (pulls `docker.io/ollama/ollama`):

```bash
cd ezansi-capability-llm-ollama
podman-compose -f podman-compose.[your-hardware].yml up -d # example: podman-compose -f podman.compose.pi5.yml up -d
./scripts/pull-model.sh mistral # or any other model you want to use
```

Start Retrieval (pulls `docker.io/chromadb/chroma:0.5.20` and builds the capability API image):

```bash
cd ../ezansi-capability-retrieval-chromadb
./scripts/deploy.sh --profile pi5  # or: pi4, amd64
./scripts/validate-deployment.sh
```

Note: the first embeddings request may download model files; it is cached in a persistent volume.

### 3) Make capability contracts visible to platform-core

Platform-core discovers contracts by scanning its `./capabilities` folder (mounted into the gateway container).

```bash
cd ../ezansi-platform-core
mkdir -p capabilities/ollama-llm capabilities/chromadb-retrieval
cp ../ezansi-capability-llm-ollama/capability.json capabilities/ollama-llm/capability.json
cp ../ezansi-capability-retrieval-chromadb/capability.json capabilities/chromadb-retrieval/capability.json
```

### 4) Build + start the platform gateway

`podman-compose.yml` builds the image locally (from `Containerfile`). Always include `--build` on cold start.

```bash
podman-compose up -d --build
```

### 5) Validate (health, discovery, routing)

```bash
./scripts/smoke-test.sh
```

If you prefer to check manually:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/registry
curl -fsS 'http://localhost:8000/status?refresh=true'
curl -fsS -X POST http://localhost:8000/validate/stack \
  -H 'Content-Type: application/json' \
  -d '{"types":["text-generation","vector-search"]}'
```

### 6) Teardown

```bash
cd ../ezansi-platform-core && podman-compose down
cd ../ezansi-capability-retrieval-chromadb && ./scripts/stop.sh --down
cd ../ezansi-capability-llm-ollama && ./scripts/stop.sh --down
```

---

## Overview

The test suite validates the platform from initial setup through MVP functionality, covering:

- **Core Platform Tests**: Basic platform operations (health, discovery, routing, validation)
- **Role-Based Scenarios**: User workflows from different perspectives
- **Hardware-Specific Tests**: Raspberry Pi 5 deployment validation
- **Integration Tests**: Multi-capability composition scenarios

## Test Categories

### 1. Core Platform Tests (`tests/e2e/test_platform_core.py`)

Validates fundamental platform operations:

- ✅ Platform startup and health checks
- ✅ Capability discovery and registry
- ✅ Request routing to capabilities
- ✅ Resource validation for stacks
- ✅ Error handling and edge cases

**Run with:**
```bash
pytest tests/e2e/test_platform_core.py -v -m e2e
```

### 2. Role-Based Scenario Tests (`tests/scenarios/test_role_based.py`)

Simulates real user workflows:

- **Developer**: Platform setup and capability deployment
- **End User**: Discovering and using AI capabilities
- **Admin**: Resource management and stack validation
- **Integration Engineer**: Composing multi-capability workflows

**Run with:**
```bash
pytest tests/scenarios/test_role_based.py -v -m scenario
```

### 3. Raspberry Pi 5 Hardware Tests (`tests/e2e/test_pi5_hardware.py`)

Validates platform behavior on Raspberry Pi 5:

- ✅ Pi5 resource constraint validation (4GB, 8GB, and 16GB variants)
- ✅ Single capability deployment (LLM)
- ✅ Multi-capability stack (RAG: LLM + Vector DB)
- ✅ Realistic workload scenarios
- ✅ Resource limit handling
- ✅ Pi5 16GB advanced capability stacks

**Run with:**
```bash
pytest tests/e2e/test_pi5_hardware.py -v -m hardware
```

## Prerequisites

### Installation

1. Install core dependencies:
```bash
pip install -r requirements.txt
```

2. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Platform Setup

The tests use FastAPI's TestClient for isolated testing. No running containers are required for basic tests.

For integration tests with real capabilities, start the platform:

```bash
podman-compose up -d
```

## Running Tests

### Run All Tests

```bash
pytest -v
```

### Run by Category

```bash
# Core platform tests only
pytest -v -m e2e

# Role-based scenarios only
pytest -v -m scenario

# Hardware-specific tests only
pytest -v -m hardware

# Exclude slow tests
pytest -v -m "not slow"
```

### Run Specific Test Classes

```bash
# Developer scenario
pytest tests/scenarios/test_role_based.py::TestDeveloperScenario -v

# Pi5 constraints
pytest tests/e2e/test_pi5_hardware.py::TestRaspberryPi5Constraints -v

# Platform health
pytest tests/e2e/test_platform_core.py::TestPlatformHealth -v
```

### Run with Coverage

```bash
pytest --cov=ezansi_platform_core --cov-report=html --cov-report=term
```

View coverage report: `open htmlcov/index.html`

## Test Markers

The test suite uses pytest markers for categorization:

- `@pytest.mark.e2e`: End-to-end integration tests
- `@pytest.mark.scenario`: Role-based user scenario tests
- `@pytest.mark.hardware`: Hardware-specific tests (Pi5, etc.)
- `@pytest.mark.slow`: Tests that take longer to run

## User Acceptance Testing (UAT)

### Pre-Deployment Validation Checklist

Before deploying new features or changes, run this validation sequence:

1. ✅ **Core Platform Health**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestPlatformHealth -v
   ```

2. ✅ **Capability Discovery**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestCapabilityDiscovery -v
   ```

3. ✅ **Developer Workflow**
   ```bash
   pytest tests/scenarios/test_role_based.py::TestDeveloperScenario -v
   ```

4. ✅ **Resource Validation**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestStackValidation -v
   ```

5. ✅ **Pi5 Compatibility** (if deploying to Pi5)
   ```bash
   pytest tests/e2e/test_pi5_hardware.py -v
   ```

### Full User Journey Test

Run the complete end-to-end user journey:

```bash
pytest tests/scenarios/test_role_based.py::TestFullUserJourney -v
```

This test simulates: Setup → Discovery → Validation → Execution

## Hardware Testing on Raspberry Pi 5

### Prerequisites

- Raspberry Pi 5 (4GB, 8GB, or 16GB variant)
- Podman installed and configured
- Sufficient storage (64GB+ recommended)

### Testing Workflow

1. **Clone repository on Pi5:**
   ```bash
   git clone https://github.com/eZansiEdgeAI/ezansi-platform-core.git
   cd ezansi-platform-core
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

3. **Run Pi5-specific tests:**
   ```bash
   pytest tests/e2e/test_pi5_hardware.py -v
   ```

4. **Validate full deployment:**
   ```bash
   # Start platform
   podman-compose up -d
   
   # Run integration tests
   pytest tests/scenarios/test_role_based.py -v
   ```

### Expected Results by Pi5 Variant

#### Pi5 4GB
- ⚠️ Single LLM capability: May be tight
- ❌ RAG stack (LLM + Vector DB): May exceed memory limits
- ✅ Platform startup: < 5 seconds
- ✅ Capability discovery: < 1 second

#### Pi5 8GB
- ✅ Single LLM capability: Compatible
- ✅ RAG stack (LLM + Vector DB): Compatible (tight fit)
- ✅ Platform startup: < 5 seconds
- ✅ Capability discovery: < 1 second

#### Pi5 16GB
- ✅ Single LLM capability: Compatible (plenty of headroom)
- ✅ RAG stack (LLM + Vector DB): Compatible (comfortable fit)
- ✅ Complex multi-capability stacks: Compatible
- ✅ Platform startup: < 5 seconds
- ✅ Capability discovery: < 1 second

## Continuous Integration

### GitHub Actions Workflow

The test suite runs automatically on:
- Pull requests
- Pushes to main branch
- Scheduled daily runs

See `.github/workflows/tests.yml` for CI configuration.

### Local Pre-Commit Validation

Before committing changes, run:

```bash
# Quick validation
pytest tests/e2e/test_platform_core.py -v

# Full validation
pytest -v
```

## Troubleshooting

### Common Issues

**Issue: Tests fail with "No module named 'ezansi_platform_core'"**

Solution:
```bash
# Install package in development mode
pip install -e .
```

**Issue: Import errors for test fixtures**

Solution: Ensure you're running from the repository root:
```bash
cd /path/to/ezansi-platform-core
pytest tests/
```

**Issue: Capability contracts not found**

This is expected in test mode. Tests use temporary capability directories created by fixtures.

## Test Maintenance

### Adding New Tests

1. Choose appropriate test file:
   - Core functionality → `tests/e2e/test_platform_core.py`
   - User scenarios → `tests/scenarios/test_role_based.py`
   - Hardware-specific → `tests/e2e/test_pi5_hardware.py`

2. Use existing fixtures from `tests/conftest.py`

3. Add appropriate markers:
   ```python
   @pytest.mark.e2e
   @pytest.mark.scenario
   def test_new_feature(client):
       # Test implementation
       pass
   ```

### Updating Hardware Tests

When adding support for new hardware (e.g., Pi4, Jetson Nano):

1. Create new constraint fixture in `conftest.py`
2. Add new test file: `tests/e2e/test_<hardware>_hardware.py`
3. Update this guide with hardware-specific instructions

## Test Coverage Goals

- **Core Platform**: > 90% coverage
- **Critical Paths** (registry, routing, validation): 100% coverage
- **API Endpoints**: 100% coverage
- **Error Handling**: > 85% coverage

Current coverage:
```bash
pytest --cov=ezansi_platform_core --cov-report=term
```

## Related Documentation

- [Platform Architecture](../docs/architecture.md)
- [Deployment Guide](../docs/deployment-guide.md)
- [API Gateway Spec](../docs/api-gateway.md)
- [Resource Validator Spec](../docs/resource-validator.md)

## Contributing

When adding new features:

1. ✅ Write tests first (TDD approach)
2. ✅ Ensure all existing tests pass
3. ✅ Add role-based scenario test if user-facing
4. ✅ Update this guide if adding new test categories
5. ✅ Run full test suite before creating PR

## Support

For questions or issues with the test suite:
- Review test output carefully
- Check fixture setup in `conftest.py`
- Refer to pytest documentation: https://docs.pytest.org/
