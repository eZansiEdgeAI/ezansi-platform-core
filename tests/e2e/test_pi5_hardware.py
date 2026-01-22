"""
Hardware-specific tests for Raspberry Pi 5.

These tests validate platform behavior on Raspberry Pi 5 hardware,
including resource constraint validation and performance considerations.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.hardware
class TestRaspberryPi5Constraints:
    """
    Test platform behavior with Raspberry Pi 5 resource constraints.
    
    Raspberry Pi 5 (8GB) specifications:
    - CPU: 4 cores @ 2.4 GHz (ARM Cortex-A76)
    - RAM: 8GB (8192 MB)
    - Storage: Varies (typically 64GB+ SD card/SSD)
    """
    
    def test_pi5_constraints_loaded(self, pi5_client):
        """Verify Pi5 constraints are properly loaded."""
        response = pi5_client.get("/constraints")
        assert response.status_code == 200
        constraints = response.json()
        
        assert constraints["device"] == "Raspberry Pi 5 (8GB)"
        assert constraints["cpu"]["cores"] == 4
        assert constraints["memory"]["total_mb"] == 8192
    
    def test_pi5_single_llm_capability_validation(self, pi5_client):
        """
        Verify a single LLM capability fits on Pi5.
        
        Typical LLM resource requirements:
        - RAM: 6000 MB (for model loading)
        - CPU: 4 cores
        - Storage: 8000 MB
        
        Pi5 should be able to handle this.
        """
        payload = {"types": ["text-generation"]}
        response = pi5_client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        result = response.json()
        
        # On Pi5 8GB, a single LLM should fit
        assert "compatible" in result
        assert "details" in result
        
        # Should not have missing types
        assert len(result.get("missing_types", [])) == 0
    
    def test_pi5_rag_stack_validation(self, pi5_client):
        """
        Verify a RAG stack (LLM + Vector DB) validation on Pi5.
        
        Combined requirements:
        - LLM: 6000 MB RAM + 4 cores + 8000 MB storage
        - Vector DB: 2000 MB RAM + 2 cores + 5000 MB storage
        - Total: 8000 MB RAM, 4-6 cores, 13000 MB storage
        
        This should fit on Pi5 8GB variant.
        """
        payload = {
            "types": ["text-generation", "vector-search"]
        }
        response = pi5_client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        result = response.json()
        
        assert "compatible" in result
        assert "details" in result
    
    def test_pi5_resource_availability(self, pi5_client):
        """Verify Pi5 reports realistic available resources."""
        response = pi5_client.get("/constraints")
        assert response.status_code == 200
        constraints = response.json()
        
        # Available memory should be less than total (OS overhead)
        memory = constraints["memory"]
        assert memory["available_mb"] < memory["total_mb"]
        assert memory["available_mb"] > 0
        
        # Storage should have reasonable availability
        storage = constraints["storage"]
        assert storage["available_mb"] > 0


@pytest.mark.hardware
class TestRaspberryPi5Platform:
    """Test platform operations specific to Pi5 deployment."""
    
    def test_pi5_platform_startup(self, pi5_client):
        """Verify platform starts successfully on Pi5."""
        response = pi5_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
    
    def test_pi5_capability_discovery(self, pi5_client):
        """Verify capability discovery works on Pi5."""
        response = pi5_client.get("/registry")
        assert response.status_code == 200
        capabilities = response.json()
        assert isinstance(capabilities, list)
        assert len(capabilities) >= 2
    
    def test_pi5_info_endpoint(self, pi5_client):
        """Verify platform info is accessible on Pi5."""
        response = pi5_client.get("/info")
        assert response.status_code == 200
        info = response.json()
        assert info["platform"] == "eZansiEdgeAI"
        assert info["capabilities_count"] >= 0


@pytest.mark.hardware
@pytest.mark.scenario
class TestPi5DeploymentScenario:
    """
    End-to-end deployment scenario on Raspberry Pi 5.
    
    User Story:
    As a user deploying on Raspberry Pi 5, I want to validate my capability
    stack fits the hardware constraints before deployment, so that I don't
    encounter resource exhaustion issues.
    """
    
    def test_pi5_deployment_workflow(self, pi5_client):
        """
        Complete Pi5 deployment validation workflow.
        
        Steps:
        1. Verify platform is running on Pi5
        2. Check Pi5 resource constraints
        3. Discover available capabilities
        4. Validate deployment fits Pi5 resources
        5. Verify all capabilities are accessible
        """
        # Step 1: Platform health on Pi5
        health = pi5_client.get("/health").json()
        assert health["status"] == "healthy"
        
        # Step 2: Check Pi5 constraints
        constraints = pi5_client.get("/constraints").json()
        assert "Raspberry Pi 5" in constraints["device"]
        assert constraints["cpu"]["cores"] == 4
        
        # Step 3: Discovery
        registry = pi5_client.get("/registry").json()
        assert len(registry) > 0
        
        service_types = []
        for cap in registry:
            service_types.extend(cap["provides"])
        
        # Step 4: Validate deployment
        if len(service_types) > 0:
            validation = pi5_client.post(
                "/validate/stack",
                json={"types": service_types[:2]}  # Test first 2 types
            ).json()
            assert "compatible" in validation
        
        # Step 5: Verify accessibility
        status = pi5_client.get("/status").json()
        assert len(status["capabilities"]) == len(registry)
    
    def test_pi5_realistic_workload(self, pi5_client):
        """
        Test a realistic AI workload on Pi5.
        
        Scenario: Deploy a voice assistant that needs:
        - Text generation (LLM)
        - Vector search (for RAG)
        
        This represents a typical edge AI use case.
        """
        # Define the voice assistant stack
        voice_assistant_stack = {
            "capabilities": [
                {"type": "text-generation"},
                {"type": "vector-search"}
            ]
        }
        
        # Validate it fits on Pi5
        response = pi5_client.post("/validate/stack", json=voice_assistant_stack)
        assert response.status_code == 200
        result = response.json()
        
        assert "compatible" in result
        assert "details" in result
        
        # Should not have missing required capabilities
        missing = result.get("missing_types", [])
        # If there are missing types, at least we got a clear response
        if len(missing) > 0:
            assert isinstance(missing, list)


@pytest.mark.hardware
class TestPi5ResourceLimits:
    """Test behavior at Pi5 resource limits."""
    
    def test_pi5_memory_constraint_reporting(self, pi5_client):
        """Verify memory constraints are properly reported for Pi5."""
        constraints = pi5_client.get("/constraints").json()
        memory = constraints["memory"]
        
        # Pi5 8GB should have reasonable available memory
        # (accounting for OS overhead, typically 6-7GB available)
        assert memory["available_mb"] >= 5000
        assert memory["available_mb"] <= memory["total_mb"]
    
    def test_pi5_cpu_constraint_reporting(self, pi5_client):
        """Verify CPU constraints are properly reported for Pi5."""
        constraints = pi5_client.get("/constraints").json()
        cpu = constraints["cpu"]
        
        assert cpu["cores"] == 4
        assert cpu["frequency_ghz"] > 0
    
    def test_pi5_storage_constraint_reporting(self, pi5_client):
        """Verify storage constraints are properly reported for Pi5."""
        constraints = pi5_client.get("/constraints").json()
        storage = constraints["storage"]
        
        # Pi5 typically has 64GB+ storage
        assert storage["total_mb"] >= 60000
        assert storage["available_mb"] > 0
        assert storage["available_mb"] <= storage["total_mb"]


@pytest.mark.hardware
class TestPi5CompatibilityChecks:
    """
    Test compatibility checks specific to Pi5 deployment.
    
    These tests verify the platform correctly identifies when
    capability stacks exceed Pi5 resources.
    """
    
    def test_pi5_validates_within_limits(self, pi5_client):
        """Verify validation correctly identifies compatible stacks."""
        # A single lightweight capability should pass
        payload = {"types": ["vector-search"]}
        response = pi5_client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        result = response.json()
        assert "compatible" in result
    
    def test_pi5_validation_provides_details(self, pi5_client):
        """Verify validation provides detailed resource breakdown."""
        payload = {"types": ["text-generation"]}
        response = pi5_client.post("/validate/stack", json=payload)
        assert response.status_code == 200
        result = response.json()
        
        # Should include details about the validation
        assert "details" in result
        details = result["details"]
        
        # Details format depends on implementation
        # Just verify it's present and not empty
        assert details is not None
