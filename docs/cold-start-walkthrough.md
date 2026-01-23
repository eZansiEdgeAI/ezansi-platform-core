# Cold-start walkthrough (absolute beginner)

**Scope note:** This walkthrough is the “from clone to working stack” path (Podman, cold start) for running Platform Core with real capabilities.

- For the fastest manual confirmation, see the 5-minute happy path in [tests/TEST_GUIDE.md](../tests/TEST_GUIDE.md).
- For automated tests (pytest, markers, coverage), see [tests/TEST_GUIDE.md](../tests/TEST_GUIDE.md).

---

This is the full “new machine” path: install dependencies, build/pull images, run containers, validate.

## 0) Install prerequisites (Podman-only)

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

## 1) Clone the repos

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

## 2) Start the capabilities (pull/build)

Start Ollama (pulls `docker.io/ollama/ollama`):

```bash
cd ezansi-capability-llm-ollama
# Preflight: recommends the right compose preset for your device
./scripts/choose-compose.sh

# Start the stack using the recommended preset
./scripts/choose-compose.sh --run

# Optional: see recommended models for your device
./scripts/choose-compose.sh --models

# Pull a model to test with
./scripts/pull-model.sh mistral
```

Start Retrieval (pulls `docker.io/chromadb/chroma:0.5.20` and builds the capability API image):

```bash
cd ../ezansi-capability-retrieval-chromadb
./scripts/deploy.sh --profile pi5  # or: pi4, amd64
./scripts/validate-deployment.sh
```

Note: the first embeddings request may download model files; it is cached in a persistent volume.

## 3) Make capability contracts visible to platform-core

Platform-core discovers contracts by scanning its `./capabilities` folder (mounted into the gateway container).

```bash
cd ../ezansi-platform-core
mkdir -p capabilities/ollama-llm capabilities/chromadb-retrieval
cp ../ezansi-capability-llm-ollama/capability.json capabilities/ollama-llm/capability.json
cp ../ezansi-capability-retrieval-chromadb/capability.json capabilities/chromadb-retrieval/capability.json
```

## 4) Build + start the platform gateway

`podman-compose.yml` builds the image locally (from `Containerfile`). Always include `--build` on cold start.

```bash
podman-compose up -d --build
```

## 5) Validate (health, discovery, routing)

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

## 6) Teardown

```bash
cd ../ezansi-platform-core && podman-compose down
cd ../ezansi-capability-retrieval-chromadb && ./scripts/stop.sh --down
cd ../ezansi-capability-llm-ollama && ./scripts/stop.sh --down
```
