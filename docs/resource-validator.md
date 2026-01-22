# Resource Validator Design

## Overview

The Resource Validator ensures that the device has enough resources to deploy and run requested capabilities. It compares device capabilities against capability resource requirements and either approves or rejects deployments.

## Responsibilities

- **Load device constraints** — read what resources the device has
- **Parse capability requirements** — extract resource needs from capability.json
- **Compare** — check if device has enough to satisfy capability
- **Validate deployment** — ensure multi-capability stacks fit together
- **Report** — provide detailed breakdown of resource compatibility

## Device constraints

Every device declares what it has in `device-constraints.json`.

## Capability requirements

Each capability declares what it needs in `capability.json`.

Other optional contract fields (like `target_platform`, `target_platforms`, and `supported_architectures`) are treated as informational metadata and MUST NOT affect resource validation.
