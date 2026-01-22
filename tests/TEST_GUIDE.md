# End-to-End Test Suite Guide

This guide describes the end-to-end test suite for ezansi-platform-core, including setup, execution, and validation procedures.

## Overview

The test suite validates the platform from initial setup through MVP functionality, covering:

- **Core Platform Tests**: Basic platform operations (health, discovery, routing, validation)
- **Role-Based Scenarios**: User workflows from different perspectives
- **Hardware-Specific Tests**: Raspberry Pi 5 deployment validation
- **Integration Tests**: Multi-capability composition scenarios

## Test Categories

### 1. Core Platform Tests (`tests/e2e/test_platform_core.py`)

Validates fundamental platform operations:

- ✅ Platform startup and health checks
- ✅ Capability discovery and registry
- ✅ Request routing to capabilities
- ✅ Resource validation for stacks
- ✅ Error handling and edge cases

**Run with:**
```bash
pytest tests/e2e/test_platform_core.py -v -m e2e
```

### 2. Role-Based Scenario Tests (`tests/scenarios/test_role_based.py`)

Simulates real user workflows:

- **Developer**: Platform setup and capability deployment
- **End User**: Discovering and using AI capabilities
- **Admin**: Resource management and stack validation
- **Integration Engineer**: Composing multi-capability workflows

**Run with:**
```bash
pytest tests/scenarios/test_role_based.py -v -m scenario
```

### 3. Raspberry Pi 5 Hardware Tests (`tests/e2e/test_pi5_hardware.py`)

Validates platform behavior on Raspberry Pi 5:

- ✅ Pi5 resource constraint validation
- ✅ Single capability deployment (LLM)
- ✅ Multi-capability stack (RAG: LLM + Vector DB)
- ✅ Realistic workload scenarios
- ✅ Resource limit handling

**Run with:**
```bash
pytest tests/e2e/test_pi5_hardware.py -v -m hardware
```

## Prerequisites

### Installation

1. Install core dependencies:
```bash
pip install -r requirements.txt
```

2. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Platform Setup

The tests use FastAPI's TestClient for isolated testing. No running containers are required for basic tests.

For integration tests with real capabilities, start the platform:

```bash
podman-compose up -d
```

## Running Tests

### Run All Tests

```bash
pytest -v
```

### Run by Category

```bash
# Core platform tests only
pytest -v -m e2e

# Role-based scenarios only
pytest -v -m scenario

# Hardware-specific tests only
pytest -v -m hardware

# Exclude slow tests
pytest -v -m "not slow"
```

### Run Specific Test Classes

```bash
# Developer scenario
pytest tests/scenarios/test_role_based.py::TestDeveloperScenario -v

# Pi5 constraints
pytest tests/e2e/test_pi5_hardware.py::TestRaspberryPi5Constraints -v

# Platform health
pytest tests/e2e/test_platform_core.py::TestPlatformHealth -v
```

### Run with Coverage

```bash
pytest --cov=ezansi_platform_core --cov-report=html --cov-report=term
```

View coverage report: `open htmlcov/index.html`

## Test Markers

The test suite uses pytest markers for categorization:

- `@pytest.mark.e2e`: End-to-end integration tests
- `@pytest.mark.scenario`: Role-based user scenario tests
- `@pytest.mark.hardware`: Hardware-specific tests (Pi5, etc.)
- `@pytest.mark.slow`: Tests that take longer to run

## User Acceptance Testing (UAT)

### Pre-Deployment Validation Checklist

Before deploying new features or changes, run this validation sequence:

1. ✅ **Core Platform Health**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestPlatformHealth -v
   ```

2. ✅ **Capability Discovery**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestCapabilityDiscovery -v
   ```

3. ✅ **Developer Workflow**
   ```bash
   pytest tests/scenarios/test_role_based.py::TestDeveloperScenario -v
   ```

4. ✅ **Resource Validation**
   ```bash
   pytest tests/e2e/test_platform_core.py::TestStackValidation -v
   ```

5. ✅ **Pi5 Compatibility** (if deploying to Pi5)
   ```bash
   pytest tests/e2e/test_pi5_hardware.py -v
   ```

### Full User Journey Test

Run the complete end-to-end user journey:

```bash
pytest tests/scenarios/test_role_based.py::TestFullUserJourney -v
```

This test simulates: Setup → Discovery → Validation → Execution

## Hardware Testing on Raspberry Pi 5

### Prerequisites

- Raspberry Pi 5 (4GB or 8GB variant)
- Podman installed and configured
- Sufficient storage (64GB+ recommended)

### Testing Workflow

1. **Clone repository on Pi5:**
   ```bash
   git clone https://github.com/eZansiEdgeAI/ezansi-platform-core.git
   cd ezansi-platform-core
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

3. **Run Pi5-specific tests:**
   ```bash
   pytest tests/e2e/test_pi5_hardware.py -v
   ```

4. **Validate full deployment:**
   ```bash
   # Start platform
   podman-compose up -d
   
   # Run integration tests
   pytest tests/scenarios/test_role_based.py -v
   ```

### Expected Results on Pi5 8GB

- ✅ Single LLM capability: Compatible
- ✅ RAG stack (LLM + Vector DB): Compatible (tight fit)
- ✅ Platform startup: < 5 seconds
- ✅ Capability discovery: < 1 second

## Continuous Integration

### GitHub Actions Workflow

The test suite runs automatically on:
- Pull requests
- Pushes to main branch
- Scheduled daily runs

See `.github/workflows/tests.yml` for CI configuration.

### Local Pre-Commit Validation

Before committing changes, run:

```bash
# Quick validation
pytest tests/e2e/test_platform_core.py -v

# Full validation
pytest -v
```

## Troubleshooting

### Common Issues

**Issue: Tests fail with "No module named 'ezansi_platform_core'"**

Solution:
```bash
# Install package in development mode
pip install -e .
```

**Issue: Import errors for test fixtures**

Solution: Ensure you're running from the repository root:
```bash
cd /path/to/ezansi-platform-core
pytest tests/
```

**Issue: Capability contracts not found**

This is expected in test mode. Tests use temporary capability directories created by fixtures.

## Test Maintenance

### Adding New Tests

1. Choose appropriate test file:
   - Core functionality → `tests/e2e/test_platform_core.py`
   - User scenarios → `tests/scenarios/test_role_based.py`
   - Hardware-specific → `tests/e2e/test_pi5_hardware.py`

2. Use existing fixtures from `tests/conftest.py`

3. Add appropriate markers:
   ```python
   @pytest.mark.e2e
   @pytest.mark.scenario
   def test_new_feature(client):
       # Test implementation
       pass
   ```

### Updating Hardware Tests

When adding support for new hardware (e.g., Pi4, Jetson Nano):

1. Create new constraint fixture in `conftest.py`
2. Add new test file: `tests/e2e/test_<hardware>_hardware.py`
3. Update this guide with hardware-specific instructions

## Test Coverage Goals

- **Core Platform**: > 90% coverage
- **Critical Paths** (registry, routing, validation): 100% coverage
- **API Endpoints**: 100% coverage
- **Error Handling**: > 85% coverage

Current coverage:
```bash
pytest --cov=ezansi_platform_core --cov-report=term
```

## Related Documentation

- [Platform Architecture](../docs/phase-2-architecture/README.md)
- [Deployment Guide](../docs/deployment-guide.md)
- [API Gateway Spec](../docs/phase-2-architecture/api-gateway.md)
- [Resource Validator Spec](../docs/phase-2-architecture/resource-validator.md)

## Contributing

When adding new features:

1. ✅ Write tests first (TDD approach)
2. ✅ Ensure all existing tests pass
3. ✅ Add role-based scenario test if user-facing
4. ✅ Update this guide if adding new test categories
5. ✅ Run full test suite before creating PR

## Support

For questions or issues with the test suite:
- Review test output carefully
- Check fixture setup in `conftest.py`
- Refer to pytest documentation: https://docs.pytest.org/
