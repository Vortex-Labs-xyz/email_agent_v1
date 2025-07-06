"""
Email Agent - Intelligent Email Processing System

An AI-powered email processing system that automatically:
- Fetches unread emails from Gmail
- Categorizes emails using AI
- Generates appropriate responses  
- Saves responses as Gmail drafts
- Provides extensible architecture for future enhancements

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Email Agent System"
__description__ = "Intelligent Email Processing System with AI"

from .core.logger import get_logger, setup_logger
from .mail.gmail_client import GmailClient
from .agent.processor import EmailProcessor

__all__ = [
    "get_logger",
    "setup_logger", 
    "GmailClient",
    "EmailProcessor"
]