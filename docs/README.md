# Documentation

This folder contains operational and design documentation for `ezansi-platform-core`.

## Mental model (LEGO bricks for learning)

If you’re a teacher/lecturer or student, think of the system like LEGO:

- **Capabilities = LEGO bricks** (LLM, retrieval, etc.)
- **`capability.json` = the studs** (what each brick provides)
- **Platform Core = the baseplate/gateway** (discovers bricks and routes requests)

Start with the cold-start walkthrough: [tests/TEST_GUIDE.md](../tests/TEST_GUIDE.md)

## Quick links

- [Deployment guide](deployment-guide.md)
- [Architecture](architecture.md)
- [API gateway](api-gateway.md)
- [Capability registry](capability-registry.md)
- [Request router](request-router.md)
- [Resource validator](resource-validator.md)
- [Stack composition (blueprints)](stack-composition.md)
- [Blueprint runner (clone + start)](blueprint-runner.md)

## Decisions

- [ADR 0001: Blueprint Clone + Start Runner](decisions/0001-blueprint-runner.md)
