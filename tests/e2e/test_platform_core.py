"""
End-to-end tests for core platform functionality.

These tests validate the basic platform operations:
- Platform startup and health checks
- Capability discovery and registry
- Request routing
- Resource validation
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestPlatformHealth:
    """Test platform health and basic operations."""
    
    def test_platform_starts_successfully(self, client):
        """Verify platform can start and respond to health checks."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_s" in data
        assert data["uptime_s"] >= 0
    
    def test_platform_info_endpoint(self, client):
        """Verify platform info returns correct metadata."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "eZansiEdgeAI"
        assert "version" in data
        assert "capabilities_count" in data
        assert "uptime_s" in data
    
    def test_constraints_endpoint(self, client):
        """Verify constraints endpoint returns device info."""
        response = client.get("/constraints")
        assert response.status_code == 200
        data = response.json()
        assert "device" in data
        assert "cpu" in data
        assert "memory" in data
        assert "storage" in data


@pytest.mark.e2e
class TestCapabilityDiscovery:
    """Test capability discovery and registry functionality."""
    
    def test_registry_discovers_capabilities(self, client):
        """Verify registry discovers all capability contracts."""
        response = client.get("/registry")
        assert response.status_code == 200
        capabilities = response.json()
        assert isinstance(capabilities, list)
        assert len(capabilities) >= 2  # ollama-llm and chromadb-retrieval
        
        # Verify capability structure
        for cap in capabilities:
            assert "name" in cap
            assert "version" in cap
            assert "description" in cap
            assert "provides" in cap
            assert "endpoint" in cap
            assert "status" in cap
    
    def test_registry_filters_by_type(self, client):
        """Verify registry can filter capabilities by service type."""
        response = client.get("/registry/text-generation")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data or "name" in data
    
    def test_registry_type_not_found(self, client):
        """Verify registry returns appropriate error for unknown types."""
        response = client.get("/registry/nonexistent-type")
        # Should return empty or error depending on implementation
        assert response.status_code in [200, 404]
    
    def test_status_endpoint(self, client):
        """Verify status endpoint lists all capabilities."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
        assert len(data["capabilities"]) >= 2


@pytest.mark.e2e
class TestStackValidation:
    """Test resource validation for capability stacks."""
    
    def test_validate_single_capability_stack(self, client):
        """Verify validation of a single capability stack."""
        payload = {
            "types": ["text-generation"]
        }
        response = client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "compatible" in data
        assert "details" in data
    
    def test_validate_multi_capability_stack(self, client):
        """Verify validation of multiple capabilities."""
        payload = {
            "types": ["text-generation", "vector-search"]
        }
        response = client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "compatible" in data
        assert "details" in data
    
    def test_validate_stack_with_missing_type(self, client):
        """Verify validation handles missing capability types."""
        payload = {
            "types": ["nonexistent-type"]
        }
        response = client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["compatible"] is False
        assert "missing_types" in data
        assert "nonexistent-type" in data["missing_types"]
    
    def test_validate_stack_alternative_format(self, client):
        """Verify validation supports alternative payload format."""
        payload = {
            "capabilities": [
                {"type": "text-generation"},
                {"type": "vector-search"}
            ]
        }
        response = client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "compatible" in data


@pytest.mark.e2e
class TestRequestRouting:
    """Test request routing to capabilities."""
    
    def test_execute_with_unknown_type(self, client):
        """Verify execution fails gracefully for unknown types."""
        payload = {
            "type": "nonexistent-type",
            "payload": {}
        }
        response = client.post("/", json=payload)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        assert "available_types" in detail
    
    def test_execute_request_structure(self, client):
        """Verify execute endpoint validates request structure."""
        # Missing type field
        response = client.post("/", json={"payload": {}})
        assert response.status_code == 422  # Validation error
    
    def test_available_types_in_error(self, client):
        """Verify error response includes available capability types."""
        payload = {
            "type": "unknown-capability",
            "payload": {}
        }
        response = client.post("/", json=payload)
        assert response.status_code == 404
        data = response.json()
        detail = data["detail"]
        assert "available_types" in detail
        available_types = detail["available_types"]
        assert "text-generation" in available_types
        assert "vector-search" in available_types or "document-embedding" in available_types


@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_payload(self, client):
        """Verify platform handles invalid JSON gracefully."""
        response = client.post(
            "/validate/stack",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_empty_stack_validation(self, client):
        """Verify stack validation handles empty input."""
        response = client.post("/validate/stack", json={})
        assert response.status_code == 200
        data = response.json()
        assert "compatible" in data
    
    def test_malformed_execute_request(self, client):
        """Verify execute endpoint validates payload structure."""
        # Missing required type field
        response = client.post("/", json={})
        assert response.status_code == 422
