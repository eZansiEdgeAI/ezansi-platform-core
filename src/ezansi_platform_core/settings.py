from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    port: int
    log_level: str
    registry_path: Path
    registry_cache_ttl_seconds: int
    health_check_interval_seconds: int
    constraints_path: Path
    strict_validation: bool
    http_timeout_seconds: float
    overrides_path: Path | None


def load_settings() -> Settings:
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    registry_path = Path(os.getenv("REGISTRY_PATH", "/capabilities"))
    constraints_path = Path(os.getenv("CONSTRAINTS_PATH", "config/device-constraints.json"))

    registry_cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "30"))
    health_check_interval_seconds = int(os.getenv("HEALTH_CHECK_INTERVAL", "10"))

    strict_validation = os.getenv("STRICT_MODE", "true").lower() in {"1", "true", "yes"}

    http_timeout_seconds = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))

    overrides_env = os.getenv("OVERRIDES_PATH")
    overrides_path = Path(overrides_env) if overrides_env else None

    return Settings(
        port=port,
        log_level=log_level,
        registry_path=registry_path,
        registry_cache_ttl_seconds=registry_cache_ttl_seconds,
        health_check_interval_seconds=health_check_interval_seconds,
        constraints_path=constraints_path,
        strict_validation=strict_validation,
        http_timeout_seconds=http_timeout_seconds,
        overrides_path=overrides_path,
    )
