from pydantic import BaseSettings
import os
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Gmail API Configuration
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./email_agent.db"
    
    # Application Configuration
    secret_key: str
    debug: bool = False
    log_level: str = "INFO"
    
    # Email Processing Configuration
    max_emails_per_batch: int = 10
    email_check_interval: int = 300  # seconds
    auto_respond_enabled: bool = True
    
    # AI Agent Configuration
    default_ai_model: str = "gpt-4"
    max_response_length: int = 500
    temperature: float = 0.7
    
    # Paths
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    knowledge_base_path: str = "knowledge_base"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()