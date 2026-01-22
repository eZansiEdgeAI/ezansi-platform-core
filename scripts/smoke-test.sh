#!/usr/bin/env bash
set -euo pipefail

base_url="${PLATFORM_BASE_URL:-http://localhost:8000}"

echo "== Platform health"
curl -fsS "$base_url/health" | cat

echo "\n== Registry"
curl -fsS "$base_url/registry" | cat

echo "\n== Status (refresh health)"
curl -fsS "$base_url/status?refresh=true" | cat

echo "\n== Validate stack (text-generation + vector-search)"
curl -fsS -X POST "$base_url/validate/stack" \
  -H 'Content-Type: application/json' \
  -d '{"types":["text-generation","vector-search"]}' | cat

echo ""

cat <<'NOTE'

NOTE:
- Execution calls depend on the actual capabilities running at the endpoints declared in the mounted contracts.
- Example LLM call:
  curl -sS -X POST "$PLATFORM_BASE_URL/" -H 'Content-Type: application/json' \
    -d '{"type":"text-generation","payload":{"json":{"model":"llama3","prompt":"Hello","stream":false}}}'

- Example retrieval call:
  curl -sS -X POST "$PLATFORM_BASE_URL/" -H 'Content-Type: application/json' \
    -d '{"type":"vector-search","payload":{"endpoint":"query","params":{"collection":"student"},"json":{"query":"What is ...?","top_k":3}}}'
NOTE
