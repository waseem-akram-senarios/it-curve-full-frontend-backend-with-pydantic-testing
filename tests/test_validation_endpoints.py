"""
Integration Tests for Validation Endpoints

Tests the FastAPI validation endpoints using the unified NEMT schema.
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.nemt_trip import VALID_PAYLOAD_EXAMPLE, INVALID_PAYLOAD_EXAMPLE


class TestValidationEndpoints:
    """Test validation API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_validate_nemt_valid_payload(self, client):
        """Test NEMT validation with valid payload"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": VALID_PAYLOAD_EXAMPLE}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["error"] is None
        assert data["metadata"]["validation_mode"] == "nemt"
        assert data["metadata"]["model_type"] is not None
    
    def test_validate_nemt_invalid_payload(self, client):
        """Test NEMT validation with invalid payload"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": INVALID_PAYLOAD_EXAMPLE}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert "error" in data["error"]
        assert "details" in data["error"]
        assert data["metadata"]["validation_mode"] == "nemt"
    
    def test_validate_test_endpoint(self, client):
        """Test the test validation endpoint"""
        response = client.post(
            "/api/validate/test",
            json={"payload": VALID_PAYLOAD_EXAMPLE}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["validation_mode"] == "nemt_test"
    
    def test_get_validation_config(self, client):
        """Test getting validation configuration"""
        response = client.get("/api/validate/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation_mode"] == "nemt"
        assert data["schema_version"] == "v2"
        assert data["pydantic_version"] == "2.x"
    
    def test_get_validation_metrics(self, client):
        """Test getting validation metrics"""
        response = client.get("/api/validate/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["validation_mode"] == "nemt"
        assert "total_validations" in data
        assert "success_rate" in data
    
    def test_get_valid_example(self, client):
        """Test getting valid payload example"""
        response = client.get("/api/validate/examples/valid")
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Example valid NEMT payload"
        assert data["format"] == "NEMT Schema v2"
        assert "payload" in data
        assert data["payload"] == VALID_PAYLOAD_EXAMPLE
    
    def test_get_invalid_example(self, client):
        """Test getting invalid payload example"""
        response = client.get("/api/validate/examples/invalid")
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Example invalid NEMT payload with validation errors"
        assert data["format"] == "NEMT Schema v2"
        assert "payload" in data
        assert data["payload"] == INVALID_PAYLOAD_EXAMPLE
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/validate/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["validation_mode"] == "nemt"
        assert data["schema_version"] == "v2"
    
    def test_error_format_consistency(self, client):
        """Test that error format is consistent across endpoints"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": INVALID_PAYLOAD_EXAMPLE}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if not data["success"]:
            error = data["error"]
            # Check error structure
            assert "error" in error
            assert "details" in error
            assert isinstance(error["details"], list)
            
            # Check detail structure
            for detail in error["details"]:
                assert "loc" in detail
                assert "msg" in detail
                assert "type" in detail
    
    def test_payload_size_metadata(self, client):
        """Test that payload size is included in metadata"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": VALID_PAYLOAD_EXAMPLE}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "payload_size" in data["metadata"]
        assert isinstance(data["metadata"]["payload_size"], int)
        assert data["metadata"]["payload_size"] > 0


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests"""
        response = client.post(
            "/api/validate/nemt",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_payload_field(self, client):
        """Test handling of requests without payload field"""
        response = client.post(
            "/api/validate/nemt",
            json={"wrong_field": "value"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_empty_payload(self, client):
        """Test handling of empty payload"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": {}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
    
    def test_invalid_payload_type(self, client):
        """Test handling of invalid payload type"""
        response = client.post(
            "/api/validate/nemt",
            json={"payload": "not_a_dict"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity


class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_large_payload_handling(self, client):
        """Test handling of large payloads"""
        # Create a large payload by duplicating the valid payload
        large_payload = VALID_PAYLOAD_EXAMPLE.copy()
        large_payload["extra_details"] = "x" * 10000  # Large string
        
        response = client.post(
            "/api/validate/nemt",
            json={"payload": large_payload}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "payload_size" in data["metadata"]
        assert data["metadata"]["payload_size"] > 10000


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])

