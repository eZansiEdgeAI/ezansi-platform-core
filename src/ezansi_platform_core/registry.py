from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .contracts import CapabilityContract, parse_contract
from .overrides import Overrides


@dataclass
class CapabilityRecord:
    contract: CapabilityContract
    contract_path: Path
    api_endpoint: Optional[str] = None
    health_check: Optional[str] = None
    status: str = "unknown"  # unknown|healthy|unhealthy
    last_health_check_s: Optional[float] = None
    last_error: Optional[str] = None


class CapabilityRegistry:
    def __init__(self, registry_path: Path, cache_ttl_seconds: int, overrides: Overrides) -> None:
        self._registry_path = registry_path
        self._cache_ttl_seconds = cache_ttl_seconds
        self._overrides = overrides
        self._loaded_at_s: float = 0.0
        self._records_by_name: Dict[str, CapabilityRecord] = {}
        self._providers_by_type: Dict[str, List[str]] = {}

    def _normalize_type(self, service_type: str) -> str:
        return self._overrides.provides_aliases.get(service_type, service_type)

    def load(self, force: bool = False) -> None:
        now = time.time()
        if not force and self._loaded_at_s and (now - self._loaded_at_s) < self._cache_ttl_seconds:
            return

        records_by_name: Dict[str, CapabilityRecord] = {}
        providers_by_type: Dict[str, List[str]] = {}

        if self._registry_path.exists():
            contract_files = list(self._registry_path.rglob("capability.json"))
        else:
            contract_files = []

        for contract_path in contract_files:
            try:
                data = json.loads(contract_path.read_text(encoding="utf-8"))
                contract = parse_contract(data)

                endpoint = contract.api.endpoint if contract.api else None
                health_check = contract.api.health_check if contract.api else None

                override = self._overrides.capabilities.get(contract.name)
                if override:
                    if override.endpoint:
                        endpoint = str(override.endpoint).rstrip("/")
                    if override.health_check:
                        health_check = str(override.health_check)

                record = CapabilityRecord(
                    contract=contract,
                    contract_path=contract_path,
                    api_endpoint=endpoint,
                    health_check=health_check,
                )
                records_by_name[contract.name] = record
                for provided in contract.provides:
                    providers_by_type.setdefault(provided, []).append(contract.name)
                    normalized = self._normalize_type(provided)
                    providers_by_type.setdefault(normalized, []).append(contract.name)
            except Exception as e:  # noqa: BLE001
                # Skip invalid contracts, but keep scanning.
                continue

        # stable ordering for determinism
        for k in list(providers_by_type.keys()):
            providers_by_type[k] = sorted(set(providers_by_type[k]))

        self._records_by_name = records_by_name
        self._providers_by_type = providers_by_type
        self._loaded_at_s = now

    def list_capabilities(self) -> List[CapabilityRecord]:
        self.load()
        return sorted(self._records_by_name.values(), key=lambda r: r.contract.name)

    def get_by_type(self, service_type: str) -> Mapping[str, Any]:
        self.load()
        providers = self._providers_by_type.get(service_type, [])
        normalized = self._normalize_type(service_type)
        if normalized != service_type:
            providers = sorted(set(providers + self._providers_by_type.get(normalized, [])))
        return {
            "type": service_type,
            "normalized_type": normalized,
            "providers": providers,
        }

    def resolve_provider(self, service_type: str) -> Optional[CapabilityRecord]:
        self.load()
        providers = self._providers_by_type.get(service_type, [])
        normalized = self._normalize_type(service_type)
        if normalized != service_type:
            providers = sorted(set(providers + self._providers_by_type.get(normalized, [])))
        if not providers:
            return None
        # v1: choose first provider deterministically
        provider_name = providers[0]
        return self._records_by_name.get(provider_name)
