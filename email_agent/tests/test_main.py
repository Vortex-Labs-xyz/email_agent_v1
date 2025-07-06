"""
Basic tests for the email agent system.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os

def test_health_endpoint():
    """Test the health endpoint returns expected structure."""
    # This is a placeholder test - would need proper setup in real testing
    # For now, just testing the structure
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        from email_agent.app.main import app
        client = TestClient(app)
        
        # Mock the gmail client and email processor
        with patch('email_agent.app.main.gmail_client') as mock_gmail, \
             patch('email_agent.app.main.email_processor') as mock_processor:
            
            mock_gmail.service.users().getProfile.return_value.execute.return_value = {
                'emailAddress': 'test@example.com'
            }
            mock_processor.client = MagicMock()
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "services" in data

def test_email_processing_request_validation():
    """Test that email processing request validation works."""
    from email_agent.app.main import EmailProcessingRequest
    
    # Valid request
    valid_request = EmailProcessingRequest(max_emails=10, mark_as_read=False)
    assert valid_request.max_emails == 10
    assert valid_request.mark_as_read == False
    
    # Test default values
    default_request = EmailProcessingRequest()
    assert default_request.max_emails == 10
    assert default_request.mark_as_read == False

def test_gmail_client_initialization():
    """Test Gmail client initialization with environment variables."""
    from email_agent.mail.gmail_client import GmailClient
    
    # Test that missing credentials raise appropriate error
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing required Gmail credentials"):
            GmailClient()

def test_email_processor_initialization():
    """Test email processor initialization."""
    from email_agent.agent.processor import EmailProcessor
    
    # Test that missing OpenAI key raises appropriate error
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing OPENAI_API_KEY"):
            EmailProcessor()

def test_logger_setup():
    """Test logger setup functionality."""
    from email_agent.core.logger import setup_logger
    
    logger = setup_logger("test_logger", "INFO")
    assert logger.name == "test_logger"
    assert logger.level == 20  # INFO level is 20

if __name__ == "__main__":
    pytest.main([__file__])