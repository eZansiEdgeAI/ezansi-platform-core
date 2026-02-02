# ADR 0002: Proxy Non-JSON Capability Responses (TTS Audio)

Date: 2026-02-02
Status: Accepted

## Context

Platform-core routes requests by capability `type` and forwards them to the resolved provider.

Historically, the gateway assumed provider responses are JSON and would:

- attempt `response.json()` and wrap the result under `{ "status": ..., "data": ... }`
- fall back to embedding response text when JSON parsing fails

This breaks a common class of capability endpoints that legitimately return **binary** responses.

The immediate driver is **text-to-speech**:

- The `text-to-speech` provider (Piper/eSpeak capability) returns `audio/wav` bytes.
- When routed through platform-core, clients should be able to do `curl -o out.wav ...`.
- If platform-core always wraps provider responses in JSON, it either fails or returns a JSON wrapper that is not a WAV file.

Separately, the external `ezansi-advisor` tool prints “curl steps” and a runnable bash script for executing blueprint flows. Those outputs also assumed JSON responses and did not provide a good default for saving WAV audio.

## Decision

1. **Preserve non-JSON provider responses in the router**
   - When provider responses are not JSON (`Content-Type` not `application/json` or `+json`), the router keeps raw `bytes` and includes the upstream `Content-Type`.

2. **Proxy TTS audio directly from platform-core**
   - For requests with `type: text-to-speech`, if the provider response is a successful binary response, platform-core returns it as a raw HTTP response with the upstream `Content-Type` (typically `audio/wav`).
   - A `Content-Disposition: attachment; filename=tts.wav` header is added to make CLI usage more ergonomic.

3. **Improve advisor output for TTS**
   - `--print-steps` prints TTS steps as `curl ... -o <step>.wav`.
   - `--print-runner` writes WAV output files for TTS steps and captures `{answer_text}` from the LLM step (in addition to `{retrieved_context}` from retrieval).

## Consequences

### Positive

- Platform-core supports binary responses for real-world capability endpoints (starting with TTS).
- TTS works end-to-end through platform-core without clients needing direct access to the capability.
- Advisor output becomes “copy/paste runnable” for audio steps.

### Negative / trade-offs

- Platform-core response shape becomes **type-dependent**:
  - most types return JSON wrapper `{status,type,data,metadata}`
  - `text-to-speech` may return raw bytes on success
- Clients that always expect JSON from `POST /` must handle the `Content-Type` and/or only use this path for non-binary types.

## Alternatives considered

- Always base64-encode binary data into JSON: rejected for size overhead and poor ergonomics.
- Add a dedicated platform-core endpoint for audio proxying: deferred; type-based routing via `POST /` remains the primary interface.

