#!/usr/bin/env bash
set -euo pipefail

base_url="${PLATFORM_BASE_URL:-http://localhost:8000}"

curl -fsS "$base_url/health" | cat
curl -fsS "$base_url/info" | cat
curl -fsS "$base_url/registry" | cat
