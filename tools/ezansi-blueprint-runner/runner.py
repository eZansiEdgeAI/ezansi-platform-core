#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import yaml


@dataclass(frozen=True)
class HostInfo:
    arch: str
    ram_mb: int
    pi_model: str


@dataclass(frozen=True)
class RunProfile:
    profile_id: str  # canonical: rpi5-16g, amd64-24g, ...
    required_ram_mb: int


def _die(message: str, exit_code: int = 2) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def _run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def _capture(cmd: List[str], cwd: Optional[Path] = None) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.stdout.strip()


def _podman_rm_force(names: List[str]) -> None:
    if not names:
        return
    subprocess.run(["podman", "rm", "-f", *names], check=True)


def _load_yaml(path: Path) -> Mapping[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _die(f"YAML at {path} must be a mapping")
    return data


def _load_yaml_optional(path: Path) -> Optional[Mapping[str, Any]]:
    try:
        return _load_yaml(path)
    except Exception:
        return None


def _platform_root() -> Path:
    # runner.py lives in tools/ezansi-blueprint-runner/
    return Path(__file__).resolve().parents[2]


def _read_ram_mb() -> int:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2:
                # kB -> MB
                return int(int(parts[1]) / 1024)
    return 0


def _read_pi_model() -> str:
    model = Path("/proc/device-tree/model")
    if not model.exists():
        return ""
    raw = model.read_bytes()
    return raw.replace(b"\x00", b"").decode("utf-8", errors="ignore").strip()


def _detect_host() -> HostInfo:
    arch = os.uname().machine
    # normalize some common cases
    if arch == "x86_64":
        arch = "amd64"
    elif arch == "aarch64":
        arch = "arm64"

    return HostInfo(arch=arch, ram_mb=_read_ram_mb(), pi_model=_read_pi_model())


_CANONICAL_PROFILES: List[RunProfile] = [
    RunProfile("rpi4-8g", required_ram_mb=8 * 1024),
    RunProfile("rpi5-8g", required_ram_mb=8 * 1024),
    RunProfile("rpi5-16g", required_ram_mb=16 * 1024),
    RunProfile("amd64-24g", required_ram_mb=24 * 1024),
    RunProfile("amd64-32g", required_ram_mb=32 * 1024),
]


def _profile_required_ram_mb(profile_id: str) -> int:
    for p in _CANONICAL_PROFILES:
        if p.profile_id == profile_id:
            return p.required_ram_mb
    return 0


def _infer_canonical_profile(host: HostInfo) -> str:
    # Simple inference to get a reasonable starting point.
    if host.arch == "amd64":
        if host.ram_mb >= 32 * 1024:
            return "amd64-32g"
        return "amd64-24g"

    if host.arch in {"arm64", "armv8"}:
        if "Raspberry Pi 5" in host.pi_model or host.ram_mb >= 12 * 1024:
            return "rpi5-16g" if host.ram_mb >= 16 * 1024 else "rpi5-8g"
        return "rpi4-8g"

    # Unknown arch: pick smallest profile; capability scripts may still refuse.
    return "rpi4-8g"


def _downgrade_profile_if_needed(requested_profile: str, host: HostInfo) -> Tuple[str, bool]:
    # Returns (selected_profile, downgraded)
    req_ram = _profile_required_ram_mb(requested_profile)
    if req_ram and host.ram_mb and host.ram_mb < req_ram:
        # Downgrade within same device family if possible.
        if requested_profile.startswith("rpi5-"):
            return ("rpi5-8g" if host.ram_mb >= 8 * 1024 else "rpi4-8g"), True
        if requested_profile.startswith("amd64-"):
            return ("amd64-24g" if host.ram_mb >= 24 * 1024 else "amd64-24g"), True
        return ("rpi4-8g", True)

    return requested_profile, False


def _ensure_tools_available() -> None:
    for exe in ["git", "podman-compose"]:
        if not shutil.which(exe):
            _die(f"Required executable not found in PATH: {exe}")


def _http_ok(url: str, timeout_s: float = 2.5) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return 200 <= int(resp.status) < 300
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        http.client.HTTPException,
        TimeoutError,
        OSError,
        ValueError,
    ):
        return False


def _start_platform_core_if_needed(
    platform_core_dir: Path,
    platform_url: str,
    build: bool,
    replace_existing_containers: bool,
) -> Dict[str, Any]:
    health_url = platform_url.rstrip("/") + "/health"
    if _http_ok(health_url):
        return {"url": platform_url, "action": "already-running"}

    if not (platform_core_dir / "podman-compose.yml").exists():
        _die(f"platform-core podman-compose.yml not found under: {platform_core_dir}")

    # If platform-core uses a fixed container_name, avoid trying to recreate it.
    # - If the container is already running, wait briefly for /health instead of failing with a name collision.
    # - If the container exists but is stopped, either remove it (if --replace-existing-containers) or fail with instructions.
    compose_files = [platform_core_dir / "podman-compose.yml"]
    declared = _compose_declared_container_names(compose_files)
    if declared:
        running = set(_podman_container_names(running_only=True))
        allc = set(_podman_container_names(running_only=False))

        if all(name in running for name in declared):
            # Running but not yet healthy (or health URL not reachable); wait before taking destructive action.
            deadline = time.monotonic() + 45.0
            while time.monotonic() < deadline:
                if _http_ok(health_url, timeout_s=2.5):
                    return {"url": platform_url, "action": "already-running"}
                time.sleep(0.5)

            _die(
                f"platform-core containers are running ({', '.join(declared)}) but {health_url} is not healthy. "
                "Try: podman logs ezansi-platform-core --tail=200"
            )

        if any(name in allc for name in declared):
            existing = [n for n in declared if n in allc]
            if replace_existing_containers:
                print(
                    f"Warning: removing existing platform-core containers ({', '.join(existing)}) due to --replace-existing-containers",
                    file=sys.stderr,
                )
                _podman_rm_force(existing)
            else:
                _die(
                    f"platform-core has existing containers with fixed names ({', '.join(existing)}). "
                    "Stop/remove them first, or re-run with --replace-existing-containers."
                )

    cmd = ["podman-compose", "up", "-d"]
    if build:
        cmd.append("--build")
    _run(cmd, cwd=platform_core_dir)

    # Platform-core may briefly reset connections while the service boots.
    deadline = time.monotonic() + 45.0
    while time.monotonic() < deadline:
        if _http_ok(health_url, timeout_s=2.5):
            return {"url": platform_url, "action": "started", "build": build}
        time.sleep(0.5)

    _die(
        f"platform-core did not become healthy at {health_url}. "
        "Try: podman-compose ps && podman-compose logs --tail=200"
    )



def _podman_container_names(running_only: bool) -> List[str]:
    fmt = "{{.Names}}"
    cmd = ["podman", "ps", "--format", fmt]
    if not running_only:
        cmd.insert(2, "-a")
    out = _capture(cmd)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _compose_declared_container_names(compose_files: List[Path]) -> List[str]:
    names: List[str] = []
    for f in compose_files:
        y = _load_yaml_optional(f)
        if not y:
            continue
        services = y.get("services")
        if not isinstance(services, dict):
            continue
        for svc in services.values():
            if isinstance(svc, dict):
                cn = svc.get("container_name")
                if isinstance(cn, str) and cn.strip():
                    names.append(cn.strip())
    # preserve order but de-dupe
    seen: set[str] = set()
    out: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _git_clone_or_update(repo_url: str, dest_dir: Path, ref: str) -> None:
    if dest_dir.exists() and (dest_dir / ".git").exists():
        _run(["git", "fetch", "--all", "--prune"], cwd=dest_dir)
    else:
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", repo_url, str(dest_dir)])

    # Checkout ref (branch/tag/SHA). If it's a branch, reset to origin/<branch>.
    _run(["git", "checkout", ref], cwd=dest_dir)
    # Best-effort fast-forward when ref looks like a branch name.
    try:
        _run(["git", "pull", "--ff-only"], cwd=dest_dir)
    except subprocess.CalledProcessError:
        # Could be detached or non-tracking; that's fine.
        pass


def _catalog_entries(catalog: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    caps = catalog.get("capabilities")
    if not isinstance(caps, list):
        return []
    out: List[Mapping[str, Any]] = []
    for c in caps:
        if isinstance(c, dict):
            out.append(c)
    return out


def _resolve_capability_for_type(
    required_type: str,
    blueprint: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> str:
    hints = blueprint.get("capability_hints")
    if isinstance(hints, dict):
        hinted = hints.get(required_type)
        if isinstance(hinted, str) and hinted.strip():
            return hinted.strip()

    # If only one approved capability provides this type, pick it.
    providers: List[str] = []
    for entry in _catalog_entries(catalog):
        cap_id = str(entry.get("capability_id", "")).strip()
        types = entry.get("types")
        if not cap_id or not isinstance(types, list):
            continue
        if required_type in [str(t) for t in types]:
            providers.append(cap_id)

    if len(providers) == 1:
        return providers[0]

    if not providers:
        _die(f"No approved capability provides type '{required_type}' (catalog)")

    _die(
        f"Multiple approved capabilities provide type '{required_type}'. "
        f"Add blueprint capability_hints.{required_type} = one of: {', '.join(sorted(providers))}"
    )


def _catalog_entry_by_id(catalog: Mapping[str, Any], capability_id: str) -> Mapping[str, Any]:
    for entry in _catalog_entries(catalog):
        if str(entry.get("capability_id", "")).strip() == capability_id:
            return entry
    _die(f"Capability '{capability_id}' not found in catalog")


def _select_profile(blueprint: Mapping[str, Any], cli_profile: Optional[str], strict: bool) -> str:
    host = _detect_host()

    requested = cli_profile
    if not requested:
        target_device = blueprint.get("target_device")
        if isinstance(target_device, dict):
            p = target_device.get("profile")
            if isinstance(p, str) and p.strip():
                requested = p.strip()

    if not requested or requested == "auto":
        requested = _infer_canonical_profile(host)

    if requested not in {p.profile_id for p in _CANONICAL_PROFILES}:
        _die(
            f"Unsupported profile '{requested}'. Supported: "
            + ", ".join(p.profile_id for p in _CANONICAL_PROFILES)
        )

    selected, downgraded = _downgrade_profile_if_needed(requested, host)
    if downgraded:
        msg = (
            f"Requested profile '{requested}' requires ~{_profile_required_ram_mb(requested)}MB RAM; "
            f"detected {host.ram_mb}MB. Selected '{selected}'."
        )
        if strict:
            _die(msg + " Use a smaller profile or omit --strict.")
        print("Warning: " + msg, file=sys.stderr)

    return selected


def _start_capability_from_repo(
    capability_id: str,
    repo_dir: Path,
    selected_profile: str,
    catalog_entry: Mapping[str, Any],
    run_project: str,
    build: bool,
    replace_existing_containers: bool,
) -> Dict[str, Any]:
    start = catalog_entry.get("start")
    if not isinstance(start, dict):
        _die(f"Catalog entry for {capability_id} missing start")

    kind = str(start.get("kind", "")).strip()
    script_rel = str(start.get("script", "")).strip()
    args = start.get("args") if isinstance(start.get("args"), dict) else {}

    if kind not in {"choose-compose", "compose"}:
        _die(f"Unsupported start.kind '{kind}' for {capability_id}")

    def _ensure_no_container_name_conflicts(compose_files: List[Path]) -> List[str]:
        declared = _compose_declared_container_names(compose_files)
        if not declared:
            return []

        running = set(_podman_container_names(running_only=True))
        allc = set(_podman_container_names(running_only=False))

        if all(name in running for name in declared):
            print(
                f"Warning: {capability_id} containers already running ({', '.join(declared)}); skipping start",
                file=sys.stderr,
            )
            return declared

        if any(name in allc for name in declared):
            existing = [n for n in declared if n in allc]
            if replace_existing_containers:
                print(
                    f"Warning: removing existing containers for {capability_id} ({', '.join(existing)}) due to --replace-existing-containers",
                    file=sys.stderr,
                )
                _podman_rm_force(existing)
            else:
                _die(
                    f"{capability_id} has existing containers with fixed names ({', '.join(declared)}). "
                    "Stop/remove them first, use the same running stack, or re-run with --replace-existing-containers."
                )

        return declared

    def _maybe_run_preflight() -> Optional[Dict[str, Any]]:
        preflight = start.get("preflight")
        if not isinstance(preflight, dict):
            return None

        script = str(preflight.get("script", "")).strip()
        if not script:
            return None

        optional = bool(preflight.get("optional", False))
        pf_args = preflight.get("args")
        if not isinstance(pf_args, list):
            pf_args = []

        script_path = repo_dir / script
        if not script_path.exists():
            msg = f"Missing preflight script for {capability_id}: {script}"
            if optional:
                print("Warning: " + msg, file=sys.stderr)
                return {"script": script, "optional": True, "status": "missing"}
            _die(msg)

        cmd = ["bash", str(script_path)] + [str(x) for x in pf_args]
        try:
            _run(cmd, cwd=repo_dir)
            return {"script": script, "optional": optional, "status": "ok"}
        except subprocess.CalledProcessError as e:
            if optional:
                print(
                    f"Warning: preflight script failed for {capability_id} ({script}): exit {e.returncode}",
                    file=sys.stderr,
                )
                return {"script": script, "optional": True, "status": "failed", "exit_code": e.returncode}
            raise

    if kind == "compose":
        preflight_info = _maybe_run_preflight()

        compose_rel = start.get("compose_files")
        if compose_rel is None:
            compose_rel = ["podman-compose.yml"]

        if not isinstance(compose_rel, list) or not compose_rel:
            _die(f"Catalog start.compose_files for {capability_id} must be a non-empty list")

        compose_files: List[Path] = []
        for rel in compose_rel:
            if not isinstance(rel, str) or not rel.strip():
                _die(f"Catalog start.compose_files for {capability_id} contains a non-string entry")
            p = repo_dir / rel.strip()
            if not p.exists():
                _die(f"Missing compose file for {capability_id}: {rel}")
            compose_files.append(p)

        declared = _ensure_no_container_name_conflicts(compose_files)
        if declared and all(name in set(_podman_container_names(running_only=True)) for name in declared):
            return {
                "kind": "existing-containers",
                "files": [str(p) for p in compose_files],
                "project": run_project,
                "container_names": declared,
                "preflight": preflight_info,
            }

        up_cmd = ["podman-compose", "-p", run_project]
        for f in compose_files:
            up_cmd += ["-f", str(f)]
        up_cmd += ["up", "-d"]
        if build:
            up_cmd.append("--build")

        _run(up_cmd, cwd=repo_dir)
        return {
            "kind": "podman-compose",
            "files": [str(p) for p in compose_files],
            "project": run_project,
            "build": build,
            "container_names": declared,
            "preflight": preflight_info,
        }

    script_path = repo_dir / script_rel
    if not script_path.exists():
        _die(f"Missing selector script for {capability_id}: {script_rel}")

    # Determine repo-specific profile arguments.
    device_map = args.get("device_map") if isinstance(args.get("device_map"), dict) else {}
    profile_map = args.get("profile_map") if isinstance(args.get("profile_map"), dict) else {}

    cmd: List[str] = ["bash", str(script_path)]

    # Prefer device_map (fine-grained tiers); otherwise use profile_map.
    if device_map:
        device_name = device_map.get(selected_profile)
        if not isinstance(device_name, str) or not device_name.strip():
            _die(f"No device_map entry for profile '{selected_profile}' in {capability_id}")
        override = device_name.strip()
        cmd += ["--device", override, "--quiet"]
        compose_rel = _capture(cmd, cwd=repo_dir)
        compose_file = repo_dir / compose_rel
        if not compose_file.exists():
            _die(f"Selector returned missing compose file: {compose_rel}")

        compose_files = [compose_file]
        declared = _compose_declared_container_names(compose_files)
        if declared:
            running = set(_podman_container_names(running_only=True))
            allc = set(_podman_container_names(running_only=False))
            if all(name in running for name in declared):
                print(
                    f"Warning: {capability_id} containers already running ({', '.join(declared)}); skipping start",
                    file=sys.stderr,
                )
                return {
                    "kind": "existing-containers",
                    "files": [str(p) for p in compose_files],
                    "project": run_project,
                    "container_names": declared,
                }
            if any(name in allc for name in declared):
                existing = [n for n in declared if n in allc]
                if replace_existing_containers:
                    print(
                        f"Warning: removing existing containers for {capability_id} ({', '.join(existing)}) due to --replace-existing-containers",
                        file=sys.stderr,
                    )
                    _podman_rm_force(existing)
                else:
                    _die(
                        f"{capability_id} has existing containers with fixed names ({', '.join(declared)}). "
                        "Stop/remove them first, use the same running stack, or re-run with --replace-existing-containers."
                    )

        up_cmd = ["podman-compose", "-p", run_project, "-f", str(compose_file), "up", "-d"]
        if build:
            up_cmd.append("--build")

        _run(up_cmd, cwd=repo_dir)
        return {
            "kind": "podman-compose",
            "files": [str(compose_file)],
            "project": run_project,
            "build": build,
            "container_names": declared,
        }

    if profile_map:
        coarse = profile_map.get(selected_profile)
        if not isinstance(coarse, str) or not coarse.strip():
            _die(f"No profile_map entry for profile '{selected_profile}' in {capability_id}")

        coarse_name = coarse.strip()
        override_rel = _capture(["bash", str(script_path), "--profile", coarse_name, "--quiet"], cwd=repo_dir)
        override_file = repo_dir / override_rel
        base_file = repo_dir / "podman-compose.yml"

        if not base_file.exists():
            _die(f"Missing base compose file in {capability_id}: podman-compose.yml")
        if not override_file.exists():
            _die(f"Selector returned missing override file: {override_rel}")

        compose_files = [base_file, override_file]
        declared = _compose_declared_container_names(compose_files)
        if declared:
            running = set(_podman_container_names(running_only=True))
            allc = set(_podman_container_names(running_only=False))
            if all(name in running for name in declared):
                print(
                    f"Warning: {capability_id} containers already running ({', '.join(declared)}); skipping start",
                    file=sys.stderr,
                )
                return {
                    "kind": "existing-containers",
                    "files": [str(p) for p in compose_files],
                    "project": run_project,
                    "container_names": declared,
                }
            if any(name in allc for name in declared):
                existing = [n for n in declared if n in allc]
                if replace_existing_containers:
                    print(
                        f"Warning: removing existing containers for {capability_id} ({', '.join(existing)}) due to --replace-existing-containers",
                        file=sys.stderr,
                    )
                    _podman_rm_force(existing)
                else:
                    _die(
                        f"{capability_id} has existing containers with fixed names ({', '.join(declared)}). "
                        "Stop/remove them first, use the same running stack, or re-run with --replace-existing-containers."
                    )

        up_cmd = [
            "podman-compose",
            "-p",
            run_project,
            "-f",
            str(base_file),
            "-f",
            str(override_file),
            "up",
            "-d",
        ]
        if build:
            up_cmd.append("--build")

        _run(up_cmd, cwd=repo_dir)
        return {
            "kind": "podman-compose",
            "files": [str(base_file), str(override_file)],
            "project": run_project,
            "build": build,
            "container_names": declared,
        }

    _die(f"Catalog start.args for {capability_id} must include device_map or profile_map")


def _default_run_id(blueprint: Mapping[str, Any]) -> str:
    bid = str(blueprint.get("id", "blueprint")).strip() or "blueprint"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{bid}-{ts}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_apply(args: argparse.Namespace) -> None:
    _ensure_tools_available()

    blueprint_path = Path(args.blueprint).expanduser().resolve()
    if not blueprint_path.exists():
        _die(f"Blueprint not found: {blueprint_path}")

    catalog_path = Path(args.catalog).expanduser().resolve()
    if not catalog_path.exists():
        _die(f"Catalog not found: {catalog_path}")

    blueprint = _load_yaml(blueprint_path)
    catalog = _load_yaml(catalog_path)

    required_types = blueprint.get("requires_types")
    if not isinstance(required_types, list) or not required_types:
        _die("Blueprint missing requires_types")

    selected_profile = _select_profile(blueprint, args.profile, args.strict)

    platform_info: Optional[Dict[str, Any]] = None
    if args.start_platform_core:
        platform_info = _start_platform_core_if_needed(
            platform_core_dir=Path(args.platform_core_dir).expanduser().resolve(),
            platform_url=args.platform_url,
            build=bool(args.platform_build),
            replace_existing_containers=bool(args.replace_existing_containers),
        )

    run_id = args.run_id or _default_run_id(blueprint)
    runs_dir = Path(args.runs_dir).expanduser().resolve()
    run_dir = runs_dir / run_id

    run_dir.mkdir(parents=True, exist_ok=True)
    repos_dir = run_dir / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)

    # Resolve types -> capability IDs
    cap_ids: List[str] = []
    for t in [str(x) for x in required_types]:
        cap_ids.append(_resolve_capability_for_type(t, blueprint, catalog))

    # Start each capability
    started: List[Dict[str, Any]] = []

    for cap_id in sorted(set(cap_ids)):
        entry = _catalog_entry_by_id(catalog, cap_id)
        repo_url = str(entry.get("repo", "")).strip()
        ref = str(entry.get("default_ref", "main")).strip() or "main"

        if not repo_url:
            _die(f"Catalog entry for {cap_id} missing repo")

        if ref == "main":
            print(f"Warning: using moving ref 'main' for {cap_id} (latest)", file=sys.stderr)

        repo_dir = repos_dir / cap_id
        _git_clone_or_update(repo_url, repo_dir, ref)

        build_recommended = False
        start_cfg = entry.get("start") if isinstance(entry.get("start"), dict) else {}
        start_args = start_cfg.get("args") if isinstance(start_cfg.get("args"), dict) else {}
        if isinstance(start_args.get("build_recommended"), bool):
            build_recommended = bool(start_args.get("build_recommended"))

        do_build = build_recommended if args.build is None else bool(args.build)
        project = f"ezansi-{run_id}-{cap_id}".replace("_", "-")

        deployment = _start_capability_from_repo(
            capability_id=cap_id,
            repo_dir=repo_dir,
            selected_profile=selected_profile,
            catalog_entry=entry,
            run_project=project,
            build=do_build,
            replace_existing_containers=bool(args.replace_existing_containers),
        )

        started.append(
            {
                "capability_id": cap_id,
                "repo": repo_url,
                "ref": ref,
                "repo_dir": str(repo_dir),
                "deployment": deployment,
            }
        )

    state = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blueprint": str(blueprint_path),
        "catalog": str(catalog_path),
        "selected_profile": selected_profile,
        "platform": platform_info,
        "capabilities": started,
    }

    _write_json(run_dir / "state.json", state)

    print(f"Run created: {run_dir}")
    print(f"Selected profile: {selected_profile}")
    if platform_info:
        print(f"Platform: {platform_info.get('url')} ({platform_info.get('action')})")
    print("Capabilities started:")
    for c in started:
        print(f"- {c['capability_id']}")


def _load_state(run_dir: Path) -> Mapping[str, Any]:
    state_path = run_dir / "state.json"
    if not state_path.exists():
        _die(f"state.json not found in run dir: {run_dir}")
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _die("Invalid state.json")
    return data


def cmd_status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).expanduser().resolve()
    state = _load_state(run_dir)
    print(json.dumps(state, indent=2, sort_keys=True))


def cmd_destroy(args: argparse.Namespace) -> None:
    _ensure_tools_available()

    run_dir = Path(args.run_dir).expanduser().resolve()
    state = _load_state(run_dir)

    caps = state.get("capabilities")
    if not isinstance(caps, list):
        _die("Invalid state.json: capabilities")

    errors: List[str] = []

    for c in caps:
        if not isinstance(c, dict):
            continue
        deployment = c.get("deployment")
        if not isinstance(deployment, dict):
            continue
        project = deployment.get("project")
        files = deployment.get("files")
        repo_dir = c.get("repo_dir")

        if not isinstance(project, str) or not project:
            continue
        if not isinstance(repo_dir, str) or not repo_dir:
            continue

        # Use the same compose files that were used for up.
        down_cmd: List[str] = ["podman-compose", "-p", project]
        if isinstance(files, list):
            for f in files:
                if isinstance(f, str) and f:
                    down_cmd += ["-f", f]

        down_cmd += ["down"]
        if args.volumes:
            down_cmd += ["-v"]

        try:
            _run(down_cmd, cwd=Path(repo_dir))
        except subprocess.CalledProcessError as e:
            errors.append(f"{project}: {e}")

    if errors:
        _die("Some projects failed to stop:\n" + "\n".join(errors), exit_code=1)

    print(f"Stopped projects for run: {run_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ezansi-blueprint-runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_apply = sub.add_parser("apply", help="Clone and start required capability repos")
    p_apply.add_argument("--blueprint", required=True)
    p_apply.add_argument(
        "--catalog",
        default=str(_platform_root() / "capabilities" / "catalog.yml"),
        help="Path to approved capability catalog",
    )
    p_apply.add_argument(
        "--runs-dir",
        default=str(Path.cwd() / ".ezansi-runs"),
        help="Project-local runs directory",
    )
    p_apply.add_argument("--run-id", default=None, help="Optional run id (default: <blueprint-id>-<timestamp>")
    p_apply.add_argument(
        "--profile",
        default=None,
        help="Canonical profile id (auto, rpi4-8g, rpi5-8g, rpi5-16g, amd64-24g, amd64-32g)",
    )
    p_apply.add_argument("--strict", action="store_true", help="Fail fast if requirements/profile are not met")

    p_apply.add_argument(
        "--start-platform-core",
        action="store_true",
        help="Start platform-core via podman-compose (if not already healthy)",
    )
    p_apply.add_argument(
        "--platform-url",
        default="http://localhost:8000",
        help="Platform-core base URL for health check",
    )
    p_apply.add_argument(
        "--platform-core-dir",
        default=str(_platform_root()),
        help="Path to ezansi-platform-core repo (for podman-compose up)",
    )
    p_apply.add_argument(
        "--platform-build",
        action="store_true",
        help="Use --build when starting platform-core",
    )

    p_apply.add_argument(
        "--replace-existing-containers",
        action="store_true",
        help=(
            "If a capability (or platform-core) uses fixed container_name values and those containers already exist, "
            "remove them with 'podman rm -f' before starting. Use with care."
        ),
    )

    build_group = p_apply.add_mutually_exclusive_group()
    build_group.add_argument("--build", dest="build", action="store_true", default=None, help="Force --build")
    build_group.add_argument("--no-build", dest="build", action="store_false", default=None, help="Force no --build")

    p_apply.set_defaults(func=cmd_apply)

    p_status = sub.add_parser("status", help="Print run state")
    p_status.add_argument("--run-dir", required=True)
    p_status.set_defaults(func=cmd_status)

    p_destroy = sub.add_parser("destroy", help="Stop all compose projects for a run")
    p_destroy.add_argument("--run-dir", required=True)
    p_destroy.add_argument("--volumes", action="store_true", help="Also remove named/anon volumes")
    p_destroy.set_defaults(func=cmd_destroy)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
