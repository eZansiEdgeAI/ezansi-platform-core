# Request Router Design

## Overview

The Request Router accepts client requests and routes them to the appropriate capability based on what service is requested. It acts as a dispatcher that knows how to reach each capability from the registry.

## Responsibilities

- **Accept requests** — handle incoming HTTP requests for various services
- **Identify capability** — determine which capability is needed
- **Validate request** — check request format matches capability API
- **Proxy request** — forward to capability endpoint
- **Transform response** — convert response back to client format
- **Error handling** — return appropriate error if capability unavailable

## Request flow

```
Client: {"type": "text-generation", ...}
    ↓
Router checks registry: "text-generation" → provider
    ↓
Router proxies to provider endpoint
    ↓
Capability returns response
    ↓
Router returns to client
```

## Request format

All requests include a `type` field indicating which service is needed.

```json
POST /
{
  "type": "text-generation",
  "payload": {
    "endpoint": "generate",
    "json": {
      "model": "mistral",
      "prompt": "Hello",
      "stream": false
    }
  }
}
```

The router prefers routing by named contract endpoint (`payload.endpoint`).
