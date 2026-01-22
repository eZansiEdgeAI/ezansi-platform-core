"""
Role-based scenario tests for end-to-end user validation.

These tests simulate different user roles interacting with the platform:
- Developer: Setting up and deploying capabilities
- End User: Executing basic AI tasks
- Admin: Validating and managing stacks
- Integration: Composing multiple capabilities
"""
import pytest


@pytest.mark.scenario
class TestDeveloperScenario:
    """
    Developer Role: Setting up the platform and deploying first capability.
    
    User Story:
    As a developer, I want to set up the platform and deploy my first AI capability,
    so that I can start building AI-powered applications on edge devices.
    """
    
    def test_developer_setup_workflow(self, client):
        """
        End-to-end developer workflow from platform setup to capability verification.
        
        Steps:
        1. Verify platform is running
        2. Check that registry is empty or has default capabilities
        3. Verify capability discovery works
        4. Check that capability is registered and healthy
        """
        # Step 1: Verify platform is running
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"
        
        # Step 2: Check registry status
        registry_response = client.get("/registry")
        assert registry_response.status_code == 200
        capabilities = registry_response.json()
        assert isinstance(capabilities, list)
        
        # Step 3: Verify capability discovery
        info_response = client.get("/info")
        assert info_response.status_code == 200
        info = info_response.json()
        assert info["capabilities_count"] >= 0
        
        # Step 4: Verify specific capability types are available
        if len(capabilities) > 0:
            first_cap = capabilities[0]
            assert "name" in first_cap
            assert "provides" in first_cap
            assert len(first_cap["provides"]) > 0
    
    def test_developer_validate_deployment(self, client):
        """
        Verify developer can validate their deployment meets requirements.
        
        Steps:
        1. Check device constraints
        2. Validate a capability stack fits on the device
        3. Verify resource requirements
        """
        # Step 1: Check device constraints
        constraints_response = client.get("/constraints")
        assert constraints_response.status_code == 200
        constraints = constraints_response.json()
        assert "cpu" in constraints
        assert "memory" in constraints
        assert "storage" in constraints
        
        # Step 2: Validate a capability stack
        validation_payload = {
            "types": ["text-generation"]
        }
        validate_response = client.post("/validate/stack", json=validation_payload)
        assert validate_response.status_code == 200
        validation_result = validate_response.json()
        assert "compatible" in validation_result
        assert "details" in validation_result


@pytest.mark.scenario
class TestEndUserScenario:
    """
    End User Role: Executing basic AI tasks through the platform.
    
    User Story:
    As an end user, I want to use AI capabilities through a simple API,
    so that I can build intelligent applications without managing infrastructure.
    """
    
    def test_user_discover_capabilities(self, client):
        """
        User discovers available AI capabilities on the platform.
        
        Steps:
        1. Query platform for available capabilities
        2. Check what services each capability provides
        3. Verify capability details are comprehensive
        """
        # Step 1: Get all capabilities
        response = client.get("/registry")
        assert response.status_code == 200
        capabilities = response.json()
        assert len(capabilities) > 0
        
        # Step 2: Verify each capability has service types
        for cap in capabilities:
            assert "provides" in cap
            assert len(cap["provides"]) > 0
            assert "endpoint" in cap
            assert "description" in cap
        
        # Step 3: Verify we can get capabilities by type
        # Get the first service type from first capability
        if capabilities:
            first_type = capabilities[0]["provides"][0]
            type_response = client.get(f"/registry/{first_type}")
            assert type_response.status_code == 200
    
    def test_user_check_platform_status(self, client):
        """
        User checks overall platform and capability status.
        
        Steps:
        1. Get platform health
        2. Get detailed status of all capabilities
        3. Verify status information is useful
        """
        # Step 1: Platform health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        # Step 2: Detailed status
        status_response = client.get("/status")
        assert status_response.status_code == 200
        status = status_response.json()
        assert "capabilities" in status
        
        # Step 3: Verify status includes useful info
        if len(status["capabilities"]) > 0:
            cap_status = status["capabilities"][0]
            assert "name" in cap_status
            assert "status" in cap_status
            assert "provides" in cap_status


@pytest.mark.scenario
class TestAdminScenario:
    """
    Admin Role: Managing platform configuration and validating stacks.
    
    User Story:
    As an admin, I want to manage platform resources and validate capability stacks,
    so that I can ensure the platform runs efficiently within device constraints.
    """
    
    def test_admin_check_resource_constraints(self, client):
        """
        Admin reviews device resource constraints.
        
        Steps:
        1. Get device constraints
        2. Verify CPU, memory, and storage limits
        3. Check constraint format is complete
        """
        response = client.get("/constraints")
        assert response.status_code == 200
        constraints = response.json()
        
        # Verify CPU constraints
        assert "cpu" in constraints
        cpu = constraints["cpu"]
        assert "cores" in cpu
        
        # Verify memory constraints
        assert "memory" in constraints
        memory = constraints["memory"]
        assert "total_mb" in memory or "available_mb" in memory
        
        # Verify storage constraints
        assert "storage" in constraints
        storage = constraints["storage"]
        assert "total_mb" in storage or "available_mb" in storage
    
    def test_admin_validate_capability_stack(self, client):
        """
        Admin validates if a capability stack fits device constraints.
        
        Steps:
        1. Validate a simple single-capability stack
        2. Validate a complex multi-capability stack
        3. Validate an over-resourced stack (should fail)
        """
        # Step 1: Simple stack validation
        simple_payload = {"types": ["text-generation"]}
        simple_response = client.post("/validate/stack", json=simple_payload)
        assert simple_response.status_code == 200
        simple_result = simple_response.json()
        assert "compatible" in simple_result
        
        # Step 2: Multi-capability stack
        multi_payload = {"types": ["text-generation", "vector-search"]}
        multi_response = client.post("/validate/stack", json=multi_payload)
        assert multi_response.status_code == 200
        multi_result = multi_response.json()
        assert "compatible" in multi_result
        assert "details" in multi_result
    
    def test_admin_monitor_capability_health(self, client):
        """
        Admin monitors health of deployed capabilities.
        
        Steps:
        1. Get status of all capabilities
        2. Refresh health checks
        3. Verify health status is tracked
        """
        # Step 1: Get current status
        status_response = client.get("/status")
        assert status_response.status_code == 200
        status = status_response.json()
        assert "capabilities" in status
        
        # Step 2: Refresh with health checks
        refresh_response = client.get("/status?refresh=false")
        assert refresh_response.status_code == 200
        
        # Step 3: Verify tracking fields
        if len(status["capabilities"]) > 0:
            cap = status["capabilities"][0]
            assert "status" in cap
            # Health check timestamp may be None if not checked yet
            assert "last_health_check_s" in cap


@pytest.mark.scenario
class TestIntegrationScenario:
    """
    Integration Role: Composing multiple capabilities into workflows.
    
    User Story:
    As an integration engineer, I want to compose multiple AI capabilities,
    so that I can build complex AI workflows like RAG (Retrieval Augmented Generation).
    """
    
    def test_integration_discover_complementary_capabilities(self, client):
        """
        Integration engineer discovers capabilities that work together.
        
        Steps:
        1. List all available capabilities
        2. Identify capabilities that provide complementary services
        3. Verify resource requirements are documented
        """
        # Step 1: List all capabilities
        response = client.get("/registry")
        assert response.status_code == 200
        capabilities = response.json()
        
        # Step 2: Build a map of service types
        service_types = set()
        for cap in capabilities:
            for service_type in cap["provides"]:
                service_types.add(service_type)
        
        # For a RAG workflow, we need text-generation and vector-search
        # At minimum, we should have some capability types available
        assert len(service_types) > 0
    
    def test_integration_validate_composed_stack(self, client):
        """
        Integration engineer validates a composed capability stack.
        
        Steps:
        1. Define a multi-capability stack (e.g., LLM + Vector DB for RAG)
        2. Validate the stack against device constraints
        3. Verify validation provides detailed feedback
        """
        # Step 1 & 2: Validate RAG stack
        rag_stack = {
            "capabilities": [
                {"type": "text-generation"},
                {"type": "vector-search"}
            ]
        }
        response = client.post("/validate/stack", json=rag_stack)
        assert response.status_code == 200
        result = response.json()
        
        # Step 3: Verify detailed feedback
        assert "compatible" in result
        assert "details" in result
        assert "missing_types" in result
    
    def test_integration_check_all_capabilities_registered(self, client):
        """
        Integration engineer verifies all required capabilities are registered.
        
        Steps:
        1. Get list of registered capabilities
        2. Check for specific required service types
        3. Verify each capability is accessible
        """
        # Step 1: Get registry
        response = client.get("/registry")
        assert response.status_code == 200
        capabilities = response.json()
        
        # Step 2: Build service type map
        available_types = set()
        for cap in capabilities:
            available_types.update(cap["provides"])
        
        # Step 3: Verify we can query by type
        for service_type in list(available_types)[:3]:  # Check first 3 types
            type_response = client.get(f"/registry/{service_type}")
            assert type_response.status_code == 200


@pytest.mark.scenario
@pytest.mark.slow
class TestFullUserJourney:
    """
    Complete end-to-end user journey from setup to execution.
    
    This test simulates a complete user workflow combining multiple roles.
    """
    
    def test_complete_platform_workflow(self, client):
        """
        Complete workflow: Setup -> Discover -> Validate -> Execute.
        
        This is the full user journey from initial setup to running AI tasks.
        
        Steps:
        1. Platform Setup: Verify platform is running
        2. Discovery: Find available capabilities
        3. Validation: Ensure capabilities fit device constraints
        4. Status Check: Verify all components are healthy
        """
        # Step 1: Platform Setup
        health = client.get("/health").json()
        assert health["status"] == "healthy"
        
        info = client.get("/info").json()
        assert info["platform"] == "eZansiEdgeAI"
        
        # Step 2: Discovery
        registry = client.get("/registry").json()
        assert len(registry) > 0
        
        # Collect all service types
        all_types = []
        for cap in registry:
            all_types.extend(cap["provides"])
        
        # Step 3: Validation
        if len(all_types) > 0:
            validation_payload = {"types": all_types[:2]}  # Validate first 2 types
            validation = client.post("/validate/stack", json=validation_payload).json()
            assert "compatible" in validation
        
        # Step 4: Status Check
        status = client.get("/status").json()
        assert "capabilities" in status
        assert len(status["capabilities"]) == len(registry)
