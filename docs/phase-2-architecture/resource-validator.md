# Resource Validator Design

## Overview

The Resource Validator ensures that the device has enough resources to deploy and run requested capabilities. It compares device capabilities against capability resource requirements and either approves or rejects deployments.

## Responsibilities

- **Load device constraints** - Read what resources the device has
- **Parse capability requirements** - Extract resource needs from capability.json
- **Compare** - Check if device has enough to satisfy capability
- **Validate deployment** - Ensure multi-capability stacks fit together
- **Report** - Provide detailed breakdown of resource compatibility

## Device Constraints

Every device declares what it has in `device-constraints.json`:

```json
{
  "device": "Raspberry Pi 5 16GB",
  "cpu": {
    "cores": 4,
    "frequency_ghz": 2.4
  },
  "memory": {
    "total_mb": 16384,
    "available_mb": 12000,
    "reserved_mb": 2000
  },
  "storage": {
    "total_mb": 128000,
    "available_mb": 80000
  },
  "disk_io": {
    "type": "SSD",
    "throughput_mbps": 100
  }
}
```

## Capability Requirements

Each capability declares what it needs in `capability.json`:

```json
{
  "resources": {
    "ram_mb": 6000,
    "cpu_cores": 2,
    "storage_mb": 8000,
    "disk_io_mbps": 50
  }
}
```

Other optional contract fields (like `target_platform`, `target_platforms`, and `supported_architectures`) are treated as informational metadata and MUST NOT affect resource validation.

## Validation Logic

### Single Capability

```
Device RAM available: 12,000 MB
Capability needs:      6,000 MB
✓ Compatible (12,000 >= 6,000)
```

### Multiple Capabilities

```
Stack: STT (3GB) + LLM (6GB) + TTS (2GB)
Total needed: 11,000 MB
Available: 12,000 MB
✓ Compatible

Remaining after deployment: 1,000 MB
⚠ Low headroom - may cause swapping
```

### Constraints Checking

```python
def validate_deployment(device, capabilities):
  total_ram = sum(c.resources.ram_mb for c in capabilities)
  total_storage = sum(c.resources.storage_mb for c in capabilities)
  
  results = {
    "ram": {
      "required": total_ram,
      "available": device.memory.available_mb,
      "ok": total_ram <= device.memory.available_mb,
      "headroom_mb": device.memory.available_mb - total_ram
    },
    "storage": {
      "required": total_storage,
      "available": device.storage.available_mb,
      "ok": total_storage <= device.storage.available_mb
    },
    "cpu": {
      "cores": device.cpu.cores,
      "ok": True  # Always OK for now (oversubscription allowed)
    }
  }
  
  return {
    "compatible": all(r["ok"] for r in results.values()),
    "details": results
  }
```

## API Endpoints

**Validate single capability:**
```
POST /validate/capability
Body: { "name": "capability-llm-ollama", "version": "1.0" }
Response: {
  "compatible": true,
  "ram": { "required": 6000, "available": 12000, "ok": true },
  "storage": { "required": 8000, "available": 80000, "ok": true }
}
```

**Validate deployment stack:**
```
POST /validate/stack
Body: {
  "name": "voice-assistant",
  "capabilities": [
    { "name": "capability-stt-whisper" },
    { "name": "capability-llm-ollama" },
    { "name": "capability-tts-piper" }
  ]
}
Response: {
  "compatible": true,
  "summary": "Can deploy all 3 capabilities with 500MB headroom",
  "details": {...}
}
```

**Get device constraints:**
```
GET /constraints
Response: { "device": "...", "cpu": {...}, "memory": {...} }
```

## Smart Recommendations

```
Device: Pi 5 16GB
Available: 12,000 MB

Stack requested: LLM (12GB) + STT (3GB)
Total: 15,000 MB > 12,000 MB ✗ Not compatible

Suggestions:
- Use smaller LLM model (requires 4GB instead of 6GB)
- Remove STT capability (run in separate process)
- Deploy on Pi 5 32GB variant
```

## Warnings

```
Headroom low (<1GB remaining):
- Risk of OOM (Out of Memory) errors
- Consider removing a capability
- Add swap space (slower, not recommended)

CPU oversubscription:
- Running 6 cores worth of work on 4 cores
- Monitor performance
- Consider offloading to different device
```

## Testing Strategy

1. **Unit** - Test validation logic with mock constraints
2. **Integration** - Real device constraints vs. capability JSONs
3. **Edge cases** - Low memory, high core count, mixed configs

## Success Criteria

- [ ] Accurately validate single capability compatibility
- [ ] Correctly compute total resource needs for stacks
- [ ] Provide clear breakdown of what's compatible/not
- [ ] Suggest alternatives when incompatible
- [ ] Support new constraint types (GPU, TPU in future)
