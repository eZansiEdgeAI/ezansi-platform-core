from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import httpx

from .registry import CapabilityRecord


class RoutingError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class RouteResult:
    provider: str
    status_code: int
    data: Any
    latency_ms: int


class RequestRouter:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    async def check_health(self, record: CapabilityRecord) -> None:
        if record.api_endpoint is None or record.health_check is None:
            raise RoutingError("NO_API", f"Capability '{record.contract.name}' has no api.endpoint")

        url = f"{record.api_endpoint}{record.health_check}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                r = await client.get(url)
            except Exception as e:  # noqa: BLE001
                raise RoutingError("UNREACHABLE", "Capability health check failed", {"error": str(e), "url": url})

        if r.status_code >= 400:
            raise RoutingError(
                "UNHEALTHY",
                "Capability returned unhealthy status",
                {"status_code": r.status_code, "url": url, "body": _safe_text(r)},
            )

    async def execute(self, record: CapabilityRecord, request_body: Mapping[str, Any]) -> RouteResult:
        if record.api_endpoint is None:
            raise RoutingError("NO_API", f"Capability '{record.contract.name}' has no api.endpoint")

        service_type = str(request_body.get("type", ""))
        payload = request_body.get("payload")

        if not service_type:
            raise RoutingError("INVALID", "Missing 'type' field")

        method = "POST"

        # Preferred: route by contract endpoint name
        if isinstance(payload, Mapping) and "endpoint" in payload:
            endpoint_name = str(payload.get("endpoint") or "")
            if not endpoint_name:
                raise RoutingError("INVALID", "payload.endpoint must be a non-empty string")

            endpoint_spec = record.contract.endpoints.get(endpoint_name)
            if endpoint_spec is None:
                raise RoutingError(
                    "INVALID",
                    f"Unknown endpoint '{endpoint_name}' for capability '{record.contract.name}'",
                    {"available_endpoints": sorted(record.contract.endpoints.keys())},
                )

            method = endpoint_spec.method
            path = endpoint_spec.path

            params = payload.get("params")
            if params is not None and not isinstance(params, Mapping):
                raise RoutingError("INVALID", "payload.params must be an object")

            if params:
                try:
                    path = path.format(**{str(k): v for k, v in params.items()})
                except KeyError as e:
                    raise RoutingError(
                        "INVALID",
                        "Missing path param for endpoint",
                        {"missing": str(e), "path_template": endpoint_spec.path, "params": dict(params)},
                    )

        else:
            # Legacy fallback: infer endpoint path based on type using common defaults.
            if service_type == "text-generation":
                path = "/api/generate"
            elif service_type in {"vector-search", "text-embeddings", "embedding"}:
                if not isinstance(payload, Mapping) or "path" not in payload:
                    raise RoutingError(
                        "INVALID",
                        "Retrieval requests must provide payload.endpoint (preferred) or payload.path (legacy)",
                        {
                            "expected": {
                                "payload": {
                                    "endpoint": "query",
                                    "params": {"collection": "<collection>"},
                                    "json": {},
                                }
                            }
                        },
                    )
                path = str(payload.get("path"))
            else:
                raise RoutingError("UNSUPPORTED", f"Unsupported type '{service_type}'")

        url = f"{record.api_endpoint}{path}"
        json_body: Optional[Dict[str, Any]] = None

        if isinstance(payload, Mapping) and "json" in payload:
            json_body = payload.get("json")  # type: ignore[assignment]
        elif isinstance(payload, Mapping) and "path" in payload:
            json_body = payload.get("json")  # type: ignore[assignment]
        else:
            # default payload = request minus type
            json_body = {k: v for k, v in request_body.items() if k != "type"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.request(method, url, json=json_body)

        data: Any
        try:
            data = r.json()
        except Exception:  # noqa: BLE001
            data = {"text": _safe_text(r)}

        return RouteResult(provider=record.contract.name, status_code=r.status_code, data=data, latency_ms=0)


def _safe_text(response: httpx.Response) -> str:
    try:
        return response.text[:4096]
    except Exception:  # noqa: BLE001
        return ""
