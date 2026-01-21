from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class CapabilityApi:
    endpoint: str
    health_check: str


@dataclass(frozen=True)
class CapabilityEndpoint:
    method: str
    path: str


@dataclass(frozen=True)
class CapabilityContract:
    name: str
    version: str
    description: str
    provides: tuple[str, ...]
    api: Optional[CapabilityApi]
    endpoints: Mapping[str, CapabilityEndpoint]
    resources: Mapping[str, Any]
    raw: Mapping[str, Any]


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def parse_contract(data: Mapping[str, Any]) -> CapabilityContract:
    name = _as_str(data.get("name"))
    version = _as_str(data.get("version"))
    description = _as_str(data.get("description"))

    provides_value = data.get("provides") or []
    if not isinstance(provides_value, list):
        provides_value = [provides_value]
    provides = tuple(_as_str(p) for p in provides_value if _as_str(p))

    api_block = data.get("api")
    api: Optional[CapabilityApi] = None
    if isinstance(api_block, Mapping):
        endpoint = _as_str(api_block.get("endpoint"))
        health_check = _as_str(api_block.get("health_check", "/health"))
        if endpoint:
            api = CapabilityApi(endpoint=endpoint.rstrip("/"), health_check=health_check)

    resources = data.get("resources")
    if not isinstance(resources, Mapping):
        resources = {}

    endpoints_block = data.get("endpoints")
    endpoints: dict[str, CapabilityEndpoint] = {}
    if isinstance(endpoints_block, Mapping):
        for endpoint_name, endpoint_spec in endpoints_block.items():
            if not isinstance(endpoint_name, str) or not isinstance(endpoint_spec, Mapping):
                continue
            method = _as_str(endpoint_spec.get("method", "POST"), default="POST").upper()
            path = _as_str(endpoint_spec.get("path"))
            if path:
                endpoints[endpoint_name] = CapabilityEndpoint(method=method, path=path)

    if not name or not version or not provides:
        raise ValueError("Invalid capability contract: missing required fields (name/version/provides)")

    return CapabilityContract(
        name=name,
        version=version,
        description=description,
        provides=provides,
        api=api,
        endpoints=endpoints,
        resources=resources,
        raw=data,
    )
