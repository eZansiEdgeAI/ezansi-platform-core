from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml


@dataclass(frozen=True)
class CapabilityOverride:
    endpoint: Optional[str] = None
    health_check: Optional[str] = None


@dataclass(frozen=True)
class Overrides:
    capabilities: Mapping[str, CapabilityOverride]
    provides_aliases: Mapping[str, str]


def load_overrides(path: Optional[Path]) -> Overrides:
    if not path:
        return Overrides(capabilities={}, provides_aliases={})
    if not path.exists():
        return Overrides(capabilities={}, provides_aliases={})

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return Overrides(capabilities={}, provides_aliases={})

    cap_overrides: Dict[str, CapabilityOverride] = {}
    caps = raw.get("capabilities")
    if isinstance(caps, dict):
        for name, value in caps.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                continue
            cap_overrides[name] = CapabilityOverride(
                endpoint=value.get("endpoint"),
                health_check=value.get("health_check"),
            )

    provides_aliases: Dict[str, str] = {}
    aliases = raw.get("provides_aliases")
    if isinstance(aliases, dict):
        for alias, canonical in aliases.items():
            if isinstance(alias, str) and isinstance(canonical, str) and alias and canonical:
                provides_aliases[alias] = canonical

    return Overrides(capabilities=cap_overrides, provides_aliases=provides_aliases)
