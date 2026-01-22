"""
Pytest configuration and fixtures for end-to-end tests.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ezansi_platform_core.app import create_app
from ezansi_platform_core.settings import Settings


@pytest.fixture
def temp_capabilities_dir():
    """Create a temporary directory with sample capability contracts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        capabilities_path = Path(tmpdir) / "capabilities"
        capabilities_path.mkdir()
        
        # Create ollama-llm capability
        ollama_dir = capabilities_path / "ollama-llm"
        ollama_dir.mkdir()
        ollama_contract = {
            "name": "ollama-llm",
            "version": "1.0",
            "description": "Local LLM capability powered by Ollama",
            "provides": ["text-generation"],
            "api": {
                "endpoint": "http://localhost:11434",
                "type": "REST",
                "health_check": "/api/tags"
            },
            "endpoints": {
                "generate": {
                    "method": "POST",
                    "path": "/api/generate",
                    "input": "application/json",
                    "output": "application/json"
                }
            },
            "resources": {
                "ram_mb": 6000,
                "cpu_cores": 4,
                "storage_mb": 8000
            }
        }
        (ollama_dir / "capability.json").write_text(json.dumps(ollama_contract, indent=2))
        
        # Create chromadb-retrieval capability
        chroma_dir = capabilities_path / "chromadb-retrieval"
        chroma_dir.mkdir()
        chroma_contract = {
            "name": "chromadb-retrieval",
            "version": "1.0",
            "description": "Vector database for RAG retrieval",
            "provides": ["vector-search", "document-embedding"],
            "api": {
                "endpoint": "http://localhost:8001",
                "type": "REST",
                "health_check": "/health"
            },
            "endpoints": {
                "query": {
                    "method": "POST",
                    "path": "/query",
                    "input": "application/json",
                    "output": "application/json"
                }
            },
            "resources": {
                "ram_mb": 2000,
                "cpu_cores": 2,
                "storage_mb": 5000
            }
        }
        (chroma_dir / "capability.json").write_text(json.dumps(chroma_contract, indent=2))
        
        yield str(capabilities_path)


@pytest.fixture
def temp_constraints_file():
    """Create a temporary device constraints file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        constraints = {
            "device": "Test Device",
            "cpu": {"cores": 8, "frequency_ghz": 3.0},
            "memory": {"total_mb": 16384, "available_mb": 12000, "reserved_mb": 2000},
            "storage": {"total_mb": 128000, "available_mb": 80000}
        }
        json.dump(constraints, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def pi5_constraints_file():
    """Create Raspberry Pi 5 8GB device constraints file.
    
    Note: This fixture creates temporary constraint files for testing.
    The config/ directory contains reference examples for actual deployment.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Raspberry Pi 5 specs: 8GB variant
        constraints = {
            "device": "Raspberry Pi 5 (8GB)",
            "cpu": {"cores": 4, "frequency_ghz": 2.4},
            "memory": {"total_mb": 8192, "available_mb": 6000, "reserved_mb": 1000},
            "storage": {"total_mb": 64000, "available_mb": 50000}
        }
        json.dump(constraints, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def pi5_4gb_constraints_file():
    """Create Raspberry Pi 5 4GB device constraints file.
    
    Note: This fixture creates temporary constraint files for testing.
    The config/ directory contains reference examples for actual deployment.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Raspberry Pi 5 specs: 4GB variant
        constraints = {
            "device": "Raspberry Pi 5 (4GB)",
            "cpu": {"cores": 4, "frequency_ghz": 2.4},
            "memory": {"total_mb": 4096, "available_mb": 3000, "reserved_mb": 500},
            "storage": {"total_mb": 64000, "available_mb": 50000}
        }
        json.dump(constraints, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def pi5_16gb_constraints_file():
    """Create Raspberry Pi 5 16GB device constraints file.
    
    Note: This fixture creates temporary constraint files for testing.
    The config/ directory contains reference examples for actual deployment.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Raspberry Pi 5 specs: 16GB variant
        constraints = {
            "device": "Raspberry Pi 5 (16GB)",
            "cpu": {"cores": 4, "frequency_ghz": 2.4},
            "memory": {"total_mb": 16384, "available_mb": 14000, "reserved_mb": 1500},
            "storage": {"total_mb": 64000, "available_mb": 50000}
        }
        json.dump(constraints, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def test_settings(temp_capabilities_dir, temp_constraints_file):
    """Create test settings with temporary paths."""
    return Settings(
        port=8000,
        log_level="INFO",
        registry_path=Path(temp_capabilities_dir),
        constraints_path=Path(temp_constraints_file),
        overrides_path=None,
        registry_cache_ttl_seconds=1,
        health_check_interval_seconds=10,
        strict_validation=True,
        http_timeout_seconds=5
    )


@pytest.fixture
def pi5_settings(temp_capabilities_dir, pi5_constraints_file):
    """Create test settings with Pi5 8GB constraints."""
    return Settings(
        port=8000,
        log_level="INFO",
        registry_path=Path(temp_capabilities_dir),
        constraints_path=Path(pi5_constraints_file),
        overrides_path=None,
        registry_cache_ttl_seconds=1,
        health_check_interval_seconds=10,
        strict_validation=False,
        http_timeout_seconds=5
    )


@pytest.fixture
def pi5_4gb_settings(temp_capabilities_dir, pi5_4gb_constraints_file):
    """Create test settings with Pi5 4GB constraints."""
    return Settings(
        port=8000,
        log_level="INFO",
        registry_path=Path(temp_capabilities_dir),
        constraints_path=Path(pi5_4gb_constraints_file),
        overrides_path=None,
        registry_cache_ttl_seconds=1,
        health_check_interval_seconds=10,
        strict_validation=False,
        http_timeout_seconds=5
    )


@pytest.fixture
def pi5_16gb_settings(temp_capabilities_dir, pi5_16gb_constraints_file):
    """Create test settings with Pi5 16GB constraints."""
    return Settings(
        port=8000,
        log_level="INFO",
        registry_path=Path(temp_capabilities_dir),
        constraints_path=Path(pi5_16gb_constraints_file),
        overrides_path=None,
        registry_cache_ttl_seconds=1,
        health_check_interval_seconds=10,
        strict_validation=False,
        http_timeout_seconds=5
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app instance with test settings."""
    return create_app(test_settings)


@pytest.fixture
def client(app):
    """Create test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def pi5_client(pi5_settings):
    """Create test client with Pi5 8GB constraints."""
    app = create_app(pi5_settings)
    return TestClient(app)


@pytest.fixture
def pi5_4gb_client(pi5_4gb_settings):
    """Create test client with Pi5 4GB constraints."""
    app = create_app(pi5_4gb_settings)
    return TestClient(app)


@pytest.fixture
def pi5_16gb_client(pi5_16gb_settings):
    """Create test client with Pi5 16GB constraints."""
    app = create_app(pi5_16gb_settings)
    return TestClient(app)
