from __future__ import annotations

import argparse
import json
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

    args = parser.parse_args()
    blueprint_path = Path(args.blueprint)
    emit_path = Path(args.emit_capability_request) if args.emit_capability_request else None

    import asyncio

    result = asyncio.run(advise(args.platform.rstrip("/"), blueprint_path, emit_path))

    blueprint = _load_yaml(blueprint_path)
    defaults = blueprint.get("defaults") if isinstance(blueprint.get("defaults"), dict) else {}
    variables: Dict[str, Any] = {str(k): v for k, v in defaults.items()} if isinstance(defaults, dict) else {}

    print("Advisor summary")
    print(f"- platform: {args.platform}")
    print(f"- blueprint: {blueprint_path}")

    if result.missing_types:
        print(f"- missing_types: {result.missing_types}")
        print("  Action: deploy an existing capability that provides these types, or scaffold/request a new one.")
        if emit_path:
            print(f"  Wrote capability request: {emit_path}")

    if result.unhealthy_types:
        print(f"- unavailable_types: {result.unhealthy_types}")
        print("  Action: start the required capability containers (or fix networking/endpoints) and retry.")

    print(f"- compatible: {result.compatible}")

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

    raise SystemExit(0 if result.compatible else 1)


if __name__ == "__main__":
    main()
