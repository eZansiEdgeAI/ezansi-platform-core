# eZansi Advisor (external)

This tool is intentionally **outside** platform-core runtime.

It reads a stack blueprint (pattern) and checks whether the required capability types are available and healthy via Platform Core.

## Build

```bash
cd tools/ezansi-advisor
podman build -t localhost/ezansi-advisor:0.1.0 -f Containerfile .
```

## Run

```bash
# One-time (or if you don't already have the blueprints repo locally)
git clone https://github.com/eZansiEdgeAI/ezansi-blueprints.git

# From this repo root
cd /path/to/ezansi-platform-core

podman run --rm --network=host \
  -v "$PWD:/work" \
  -v "/path/to/ezansi-blueprints:/blueprints:ro" \
  localhost/ezansi-advisor:0.1.0 \
  --platform http://localhost:8000 \
  --blueprint /blueprints/blueprints/student-knowledge-rag.yml \
  --emit-capability-request /work/capability-request.json \
  --print-steps
```

Notes:
- If platform reports a required type as unavailable/unhealthy, the intended action is: **start the relevant capability container(s)** or fix the endpoint overrides.
- If a type is missing entirely, the advisor can emit a JSON request that can become a GitHub Issue/Jira ticket.
