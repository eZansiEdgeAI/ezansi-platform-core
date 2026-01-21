from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .overrides import load_overrides
from .registry import CapabilityRegistry
from .router import RequestRouter, RoutingError
from .settings import Settings
from .validator import ResourceValidator


class ExecuteRequest(BaseModel):
    type: str = Field(..., description="Service type (capability provides)")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Type-specific payload")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="eZansi Platform Core", version=__version__)

    overrides = load_overrides(settings.overrides_path)
    registry = CapabilityRegistry(settings.registry_path, settings.registry_cache_ttl_seconds, overrides)
    router = RequestRouter(timeout_seconds=settings.http_timeout_seconds)
    validator = ResourceValidator(settings.constraints_path, strict_mode=settings.strict_validation)

    started_at_s = time.time()

    @app.get("/health")
    def health() -> Mapping[str, Any]:
        return {"status": "healthy", "uptime_s": int(time.time() - started_at_s)}

    @app.get("/info")
    def info() -> Mapping[str, Any]:
        caps = registry.list_capabilities()
        return {
            "platform": "eZansiEdgeAI",
            "version": __version__,
            "capabilities_count": len(caps),
            "uptime_s": int(time.time() - started_at_s),
        }

    @app.get("/registry")
    def list_registry() -> List[Mapping[str, Any]]:
        caps = registry.list_capabilities()
        return [
            {
                "name": c.contract.name,
                "version": c.contract.version,
                "description": c.contract.description,
                "provides": list(c.contract.provides),
                "endpoint": c.api_endpoint,
                "status": c.status,
                "last_health_check_s": c.last_health_check_s,
                "last_error": c.last_error,
            }
            for c in caps
        ]

    @app.get("/registry/{service_type}")
    def registry_by_type(service_type: str) -> Mapping[str, Any]:
        return registry.get_by_type(service_type)

    @app.get("/registry/{service_type}/health")
    async def registry_type_health(service_type: str) -> Mapping[str, Any]:
        record = registry.resolve_provider(service_type)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "type": service_type,
                    "error": "capability not found",
                    "details": f"No capability provides '{service_type}'",
                    "code": "NOT_FOUND",
                },
            )

        record.last_health_check_s = time.time()
        try:
            await router.check_health(record)
            record.status = "healthy"
            record.last_error = None
            return {"status": "healthy", "provider": record.contract.name}
        except RoutingError as e:
            record.status = "unhealthy"
            record.last_error = e.message
            raise HTTPException(
                status_code=503,
                detail={"status": "unhealthy", "provider": record.contract.name, "code": e.code, **e.details},
            )

    @app.get("/constraints")
    def constraints() -> Mapping[str, Any]:
        return validator.load_constraints()

    @app.get("/status")
    async def status(refresh: bool = False) -> Mapping[str, Any]:
        caps = registry.list_capabilities()
        if refresh:
            for record in caps:
                record.last_health_check_s = time.time()
                try:
                    await router.check_health(record)
                    record.status = "healthy"
                    record.last_error = None
                except RoutingError as e:
                    record.status = "unhealthy"
                    record.last_error = e.message

        return {
            "device": validator.load_constraints().get("device") if isinstance(validator.load_constraints(), dict) else None,
            "capabilities": [
                {
                    "name": c.contract.name,
                    "provides": list(c.contract.provides),
                    "endpoint": c.api_endpoint,
                    "status": c.status,
                    "last_health_check_s": c.last_health_check_s,
                    "last_error": c.last_error,
                }
                for c in caps
            ],
        }

    @app.post("/validate/stack")
    def validate_stack(body: Mapping[str, Any]) -> Mapping[str, Any]:
        # body: {"capabilities": [{"type": "text-generation"}, ...]} OR {"types": [..]}
        types: List[str] = []
        if isinstance(body.get("types"), list):
            types = [str(t) for t in body.get("types")]
        elif isinstance(body.get("capabilities"), list):
            for item in body.get("capabilities"):
                if isinstance(item, Mapping) and "type" in item:
                    types.append(str(item["type"]))

        records = []
        missing: List[str] = []
        for t in types:
            record = registry.resolve_provider(t)
            if record is None:
                missing.append(t)
            else:
                records.append(record)

        result = validator.validate_stack(records)
        return {
            "compatible": result.compatible and not missing,
            "missing_types": missing,
            "details": result.details,
        }

    @app.post("/")
    async def execute(req: ExecuteRequest) -> Mapping[str, Any]:
        record = registry.resolve_provider(req.type)
        if record is None:
            available_types = sorted({p for c in registry.list_capabilities() for p in c.contract.provides})
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "type": req.type,
                    "error": "capability not found",
                    "details": f"No capability provides '{req.type}'",
                    "available_types": available_types,
                    "code": "NOT_FOUND",
                },
            )

        try:
            await router.check_health(record)
            t0 = time.time()
            result = await router.execute(record, {"type": req.type, "payload": req.payload})
            latency_ms = int((time.time() - t0) * 1000)
        except RoutingError as e:
            raise HTTPException(
                status_code=503 if e.code in {"UNREACHABLE", "UNHEALTHY"} else 400,
                detail={"status": "error", "type": req.type, "error": e.message, "code": e.code, **e.details},
            )

        return {
            "status": "success" if result.status_code < 400 else "error",
            "type": req.type,
            "data": result.data,
            "metadata": {"provider": result.provider, "latency_ms": latency_ms},
        }

    return app
