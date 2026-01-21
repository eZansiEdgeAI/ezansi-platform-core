# Stack Composition (Blueprints)

## Goal

Stacks are **experience layers** that compose existing capabilities. In the platform model, stacks do not call capabilities directly; they call the **Platform Core**.

## v1 Approach

- A stack describes its needs using the standard `provides` service types (e.g. `text-generation`, `vector-search`, `speech-to-text`).
- Platform Core discovers deployed capabilities via their contracts (`capability.json` and/or `GET /.well-known/capability.json`).
- Requests are routed by service `type` through the gateway (`POST /`).

## Blueprints

A blueprint is a small, versioned document that lists:

- required service types
- optional constraints (device, max RAM)
- any stack-level conventions (collection names, prompt templates)

Blueprints are intentionally kept **outside** platform-core so different stacks (student tutor, voice assistant, admin console) can reuse the same pattern.

In this workspace, blueprints live in the separate repository `ezansi-blueprints`.

## Advisor / Intent Layer

An optional external advisor can translate free-text goals into blueprint requirements:

1. Map intent → required service types (`provides`)
2. Query platform `/registry/{type}` to resolve providers
3. If a type is missing, either:
   - scaffold a new capability from a template, or
   - create a capability request for the organization

Platform Core remains focused on **discovery + validation + routing**.
