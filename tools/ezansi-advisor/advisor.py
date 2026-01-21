from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import httpx
import yaml


@dataclass(frozen=True)
class AdvisorResult:
    compatible: bool
    missing_types: List[str]
    unhealthy_types: List[str]


def _load_yaml(path: Path) -> Mapping[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Blueprint must be a YAML mapping")
    return data


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)]


def _render_placeholders(value: Any, variables: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        rendered = value
        for k, v in variables.items():
            rendered = rendered.replace(f"{{{k}}}", str(v))
        return rendered
    if isinstance(value, list):
        return [_render_placeholders(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: _render_placeholders(v, variables) for k, v in value.items()}
    return value


def _flow_steps(blueprint: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    flow = blueprint.get("flow")
    if not isinstance(flow, list):
        return []
    steps: List[Mapping[str, Any]] = []
    for item in flow:
        if isinstance(item, dict):
            steps.append(item)
    return steps


def _render_curl(platform_base_url: str, request_body: Mapping[str, Any]) -> str:
    # Use a heredoc to avoid shell-escaping JSON.
    body = json.dumps(request_body, indent=2)
    return (
        "curl -sS -X POST \"{base}/\" -H 'Content-Type: application/json' --data-binary @- <<'JSON'\n"
        "{body}\n"
        "JSON\n"
    ).format(base=platform_base_url.rstrip("/"), body=body)


def _contains_placeholder(value: Any, placeholder: str) -> bool:
    if isinstance(value, str):
        return placeholder in value
    if isinstance(value, list):
        return any(_contains_placeholder(v, placeholder) for v in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(v, placeholder) for v in value.values())
    return False


def _render_runner_step_with_curl(platform_base_url: str, request_body: Mapping[str, Any]) -> str:
    # A plain curl heredoc.
    return _render_curl(platform_base_url, request_body)


def _render_runner_step_with_placeholder_substitution(
    platform_base_url: str,
    request_body: Mapping[str, Any],
    placeholder: str,
    env_var: str,
) -> str:
    # Use Python so we don't have to do fragile shell JSON-escaping.
    body = json.dumps(request_body, indent=2)
    base = platform_base_url.rstrip("/")
    # Note: avoid str.format() here because the embedded Python contains braces.
    return (
        "python3 - <<'PY'\n"
        "import json, os, subprocess\n"
        f"base = {base!r}\n"
        f"placeholder = {placeholder!r}\n"
        f"replacement = os.environ.get({env_var!r}, '')\n"
        f"body = json.loads({body!r})\n"
        "def repl(x):\n"
        "    if isinstance(x, str):\n"
        "        return x.replace(placeholder, replacement)\n"
        "    if isinstance(x, list):\n"
        "        return [repl(v) for v in x]\n"
        "    if isinstance(x, dict):\n"
        "        return {k: repl(v) for k, v in x.items()}\n"
        "    return x\n"
        "body = repl(body)\n"
        "subprocess.run(\n"
        "    ['curl', '-sS', '-X', 'POST', f'{base}/', '-H', 'Content-Type: application/json', '--data-binary', '@-'],\n"
        "    input=(json.dumps(body) + '\\n').encode('utf-8'),\n"
        "    check=True,\n"
        ")\n"
        "PY\n"
    )


def _render_runner_script(platform_base_url: str, blueprint: Mapping[str, Any], variables: Mapping[str, Any]) -> str:
    steps = _flow_steps(blueprint)
    base = platform_base_url.rstrip("/")

    lines: List[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append("")
    lines.append(f"PLATFORM={base!r}")
    lines.append("export PLATFORM")
    lines.append("")
    lines.append("# This runner executes the blueprint flow through platform-core.")
    lines.append("# It captures retrieval output and substitutes {retrieved_context} automatically.")
    lines.append("")

    for step in steps:
        step_id = step.get("step")
        desc = step.get("description")
        platform_request = step.get("platform_request")
        if not isinstance(platform_request, dict):
            continue

        rendered_request = _render_placeholders(platform_request, variables)
        request_body: Dict[str, Any] = {
            "type": rendered_request.get("type"),
            "payload": rendered_request.get("payload"),
        }

        if step_id:
            lines.append(f"echo '== step: {step_id} =='")
        if desc:
            lines.append(f"echo {desc!r}")

        is_retrieve = False
        payload = request_body.get("payload")
        if isinstance(payload, dict):
            endpoint_name = payload.get("endpoint")
            is_retrieve = endpoint_name in {"query", "search", "retrieve"} or step_id in {"retrieve", "search"}

        if is_retrieve:
            # Capture the retrieval response.
            body = json.dumps(request_body, indent=2)
            lines.append("retrieve_json=$(curl -sS -X POST \"${PLATFORM}/\" -H 'Content-Type: application/json' --data-binary @- <<'JSON'\n" + body + "\nJSON\n)")
            lines.append("echo \"$retrieve_json\" | head -c 1200")
            lines.append(
                "retrieved_context=$(RETRIEVE_JSON=\"$retrieve_json\" python3 - <<'PY'\n"
                "import json, os\n"
                "\n"
                "def first_str(d, keys):\n"
                "    for k in keys:\n"
                "        v = d.get(k)\n"
                "        if isinstance(v, str) and v.strip():\n"
                "            return v.strip()\n"
                "    return None\n"
                "\n"
                "raw = os.environ.get('RETRIEVE_JSON', '')\n"
                "j = json.loads(raw)\n"
                "root = j if isinstance(j, dict) else {}\n"
                "data = root.get('data') if isinstance(root.get('data'), dict) else root\n"
                "\n"
                "parts = []\n"
                "matches = data.get('matches') if isinstance(data, dict) else None\n"
                "if isinstance(matches, list):\n"
                "    for m in matches:\n"
                "        if isinstance(m, dict):\n"
                "            t = first_str(m, ('text', 'document', 'content'))\n"
                "            if t:\n"
                "                parts.append(t)\n"
                "\n"
                "# Chroma-style: {documents: [[...]]}\n"
                "docs = data.get('documents') if isinstance(data, dict) else None\n"
                "if not parts and isinstance(docs, list):\n"
                "    for row in docs:\n"
                "        if isinstance(row, list):\n"
                "            for item in row:\n"
                "                if isinstance(item, str) and item.strip():\n"
                "                    parts.append(item.strip())\n"
                "\n"
                "print('\\n\\n'.join(parts))\n"
                "PY\n"
                ")"
            )
            lines.append("export retrieved_context")
            lines.append("")
            continue

        if _contains_placeholder(request_body, "{retrieved_context}"):
            lines.append(_render_runner_step_with_placeholder_substitution(base, request_body, "{retrieved_context}", "retrieved_context").rstrip("\n"))
        else:
            lines.append(_render_runner_step_with_curl(base, request_body).rstrip("\n"))
        lines.append("")

    return "\n".join(lines) + "\n"


def build_capability_request(missing_types: List[str], blueprint: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "kind": "capability-request",
        "requested_types": missing_types,
        "stack": {
            "id": blueprint.get("id"),
            "name": blueprint.get("name"),
            "version": blueprint.get("version"),
        },
        "notes": "No deployed capability provides these service types. Either scaffold a new capability from templates or submit this request to the organization.",
    }


async def advise(platform_base_url: str, blueprint_path: Path, emit_request_path: Optional[Path]) -> AdvisorResult:
    blueprint = _load_yaml(blueprint_path)

    required_types = _as_str_list(blueprint.get("requires_types"))
    optional_types = _as_str_list(blueprint.get("optional_types"))

    if not required_types:
        raise ValueError("Blueprint missing requires_types")

    async with httpx.AsyncClient(base_url=platform_base_url, timeout=10.0) as client:
        missing: List[str] = []
        unhealthy: List[str] = []

        for t in required_types:
            r = await client.get(f"/registry/{t}")
            if r.status_code >= 400:
                missing.append(t)
                continue
            payload = r.json()
            providers = payload.get("providers", [])
            if not providers:
                missing.append(t)
                continue

            # Health check the resolved provider (platform decides which provider is active).
            hr = await client.get(f"/registry/{t}/health")
            if hr.status_code >= 400:
                unhealthy.append(t)

        # Validate stack resources + provider availability in one call
        vr = await client.post("/validate/stack", json={"types": required_types + optional_types})
        validate_payload: Dict[str, Any] = vr.json() if vr.headers.get("content-type", "").startswith("application/json") else {}

    if missing and emit_request_path:
        req = build_capability_request(missing, blueprint)
        emit_request_path.write_text(json.dumps(req, indent=2) + "\n", encoding="utf-8")

    compatible = (not missing) and (not unhealthy) and bool(validate_payload.get("compatible", True))

    return AdvisorResult(compatible=compatible, missing_types=missing, unhealthy_types=unhealthy)


def main() -> None:
    parser = argparse.ArgumentParser(description="eZansi Advisor (external intent/pattern helper)")
    parser.add_argument(
        "--platform",
        default="http://localhost:8000",
        help="Platform Core base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--blueprint", required=True, help="Path to a stack blueprint YAML")
    parser.add_argument(
        "--emit-capability-request",
        default=None,
        help="Optional path to write a capability-request JSON if required types are missing",
    )
    parser.add_argument(
        "--print-steps",
        action="store_true",
        help="Print curl commands for each blueprint flow step",
    )
    parser.add_argument(
        "--print-runner",
        action="store_true",
        help="Print a runnable bash script that executes the blueprint flow and substitutes placeholders like {retrieved_context}",
    )

    args = parser.parse_args()
    blueprint_path = Path(args.blueprint)
    emit_path = Path(args.emit_capability_request) if args.emit_capability_request else None

    import asyncio

    result = asyncio.run(advise(args.platform.rstrip("/"), blueprint_path, emit_path))

    blueprint = _load_yaml(blueprint_path)
    defaults = blueprint.get("defaults") if isinstance(blueprint.get("defaults"), dict) else {}
    variables: Dict[str, Any] = {str(k): v for k, v in defaults.items()} if isinstance(defaults, dict) else {}

    runner_only = bool(args.print_runner) and not bool(args.print_steps)
    out = sys.stderr if runner_only else sys.stdout

    print("Advisor summary", file=out)
    print(f"- platform: {args.platform}", file=out)
    print(f"- blueprint: {blueprint_path}", file=out)

    if result.missing_types:
        print(f"- missing_types: {result.missing_types}", file=out)
        print(
            "  Action: deploy an existing capability that provides these types, or scaffold/request a new one.",
            file=out,
        )
        if emit_path:
            print(f"  Wrote capability request: {emit_path}", file=out)

    if result.unhealthy_types:
        print(f"- unavailable_types: {result.unhealthy_types}", file=out)
        print(
            "  Action: start the required capability containers (or fix networking/endpoints) and retry.",
            file=out,
        )

    print(f"- compatible: {result.compatible}", file=out)

    if args.print_steps:
        steps = _flow_steps(blueprint)
        if steps:
            print("\nBlueprint steps (curl)")
        for step in steps:
            step_id = step.get("step")
            desc = step.get("description")
            platform_request = step.get("platform_request")
            if not isinstance(platform_request, dict):
                continue
            rendered_request = _render_placeholders(platform_request, variables)
            request_body = {
                "type": rendered_request.get("type"),
                "payload": rendered_request.get("payload"),
            }

            if step_id:
                print(f"\n# step: {step_id}")
            if desc:
                print(f"# {desc}")
            print(_render_curl(args.platform.rstrip("/"), request_body))

    if args.print_runner:
        script = _render_runner_script(args.platform.rstrip("/"), blueprint, variables)
        if not runner_only:
            print("\nBlueprint runner (bash)")
        print(script, end="")

    raise SystemExit(0 if result.compatible else 1)


if __name__ == "__main__":
    main()
