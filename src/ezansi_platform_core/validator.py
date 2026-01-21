from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .registry import CapabilityRecord


@dataclass(frozen=True)
class ValidationResult:
    compatible: bool
    details: Mapping[str, Any]


class ResourceValidator:
    def __init__(self, constraints_path: Path, strict_mode: bool) -> None:
        self._constraints_path = constraints_path
        self._strict_mode = strict_mode

    def load_constraints(self) -> Mapping[str, Any]:
        if not self._constraints_path.exists():
            return {}
        return json.loads(self._constraints_path.read_text(encoding="utf-8"))

    def validate_stack(self, capabilities: List[CapabilityRecord]) -> ValidationResult:
        constraints = self.load_constraints()
        memory = constraints.get("memory", {}) if isinstance(constraints, dict) else {}
        storage = constraints.get("storage", {}) if isinstance(constraints, dict) else {}

        available_ram_mb = int(memory.get("available_mb", memory.get("total_mb", 0)) or 0)
        available_storage_mb = int(storage.get("available_mb", storage.get("total_mb", 0)) or 0)

        required_ram_mb = 0
        required_storage_mb = 0

        for record in capabilities:
            resources = record.contract.resources
            required_ram_mb += int(resources.get("ram_mb", 0) or 0)
            required_storage_mb += int(resources.get("storage_mb", 0) or 0)

        ram_ok = available_ram_mb == 0 or required_ram_mb <= available_ram_mb
        storage_ok = available_storage_mb == 0 or required_storage_mb <= available_storage_mb

        headroom_ram_mb = (available_ram_mb - required_ram_mb) if available_ram_mb else None

        compatible = ram_ok and storage_ok

        warnings: List[str] = []
        if compatible and self._strict_mode and headroom_ram_mb is not None and headroom_ram_mb < 1024:
            warnings.append("Low RAM headroom (<1024MB).")

        return ValidationResult(
            compatible=compatible if (not self._strict_mode) else (compatible and not warnings),
            details={
                "ram": {
                    "required_mb": required_ram_mb,
                    "available_mb": available_ram_mb or None,
                    "ok": ram_ok,
                    "headroom_mb": headroom_ram_mb,
                },
                "storage": {
                    "required_mb": required_storage_mb,
                    "available_mb": available_storage_mb or None,
                    "ok": storage_ok,
                },
                "warnings": warnings,
            },
        )
