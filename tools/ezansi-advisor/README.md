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
podman run --rm --network=host \
  -v /home/mcfuzzysquirrel/Projects/eZansiEdgeAI/ezansi-platform-core/examples:/examples:ro \
  localhost/ezansi-advisor:0.1.0 \
  --platform http://localhost:8000 \
  --blueprint /examples/stack-student-rag.yml \
  --emit-capability-request /examples/capability-request.json \
  --print-steps
```

Notes:
- If platform reports a required type as unavailable/unhealthy, the intended action is: **start the relevant capability container(s)** or fix the endpoint overrides.
- If a type is missing entirely, the advisor can emit a JSON request that can become a GitHub Issue/Jira ticket.
