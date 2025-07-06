import openai
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from ..core.config import settings
from ..db.models import Email, EmailResponse, Priority
from .knowledge_base import KnowledgeBaseManager

logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = settings.openai_api_key


class EmailAnalyzer:
    """Email content analyzer for extracting insights."""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
    
    def analyze_email_priority(self, email: Email) -> Priority:
        """Analyze email priority based on content and sender."""
        try:
            prompt = f"""
            Analyze the following email and determine its priority level (LOW, MEDIUM, HIGH, URGENT):
            
            Subject: {email.subject}
            From: {email.sender}
            Body: {email.body[:500]}...
            
            Consider:
            - Urgency keywords (urgent, asap, deadline, important)
            - Sender importance
            - Content type (meeting, request, notification)
            
            Return only the priority level: LOW, MEDIUM, HIGH, or URGENT
            """
            
            response = openai.ChatCompletion.create(
                model=settings.default_ai_model,
                messages=[
                    {"role": "system", "content": "You are an email priority analyzer. Respond with only the priority level."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            priority_text = response.choices[0].message.content.strip().upper()
            
            # Map to Priority enum
            priority_map = {
                'LOW': Priority.LOW,
                'MEDIUM': Priority.MEDIUM,
                'HIGH': Priority.HIGH,
                'URGENT': Priority.URGENT
            }
            
            return priority_map.get(priority_text, Priority.MEDIUM)
            
        except Exception as e:
            logger.error(f"Error analyzing email priority: {e}")
            return Priority.MEDIUM
    
    def extract_key_information(self, email: Email) -> Dict[str, Any]:
        """Extract key information from email content."""
        try:
            prompt = f"""
            Extract key information from this email:
            
            Subject: {email.subject}
            From: {email.sender}
            Body: {email.body}
            
            Extract and return in JSON format:
            - action_required: boolean
            - deadline: date if mentioned (YYYY-MM-DD format)
            - meeting_request: boolean
            - key_topics: list of main topics
            - sentiment: positive/negative/neutral
            - requires_response: boolean
            """
            
            response = openai.ChatCompletion.create(
                model=settings.default_ai_model,
                messages=[
                    {"role": "system", "content": "You are an email analyzer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error extracting key information: {e}")
            return {
                "action_required": False,
                "deadline": None,
                "meeting_request": False,
                "key_topics": [],
                "sentiment": "neutral",
                "requires_response": False
            }


class ResponseGenerator:
    """AI-powered email response generator."""
    
    def __init__(self):
        self.knowledge_base = KnowledgeBaseManager()
    
    def generate_response(self, email: Email, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate AI response for email."""
        try:
            # Get relevant knowledge base content
            relevant_knowledge = self.knowledge_base.search_relevant_content(
                email.subject + " " + email.body
            )
            
            # Build context
            context_text = ""
            if relevant_knowledge:
                context_text = f"Relevant knowledge:\n{relevant_knowledge}\n\n"
            
            if context:
                context_text += f"Additional context:\n{json.dumps(context, indent=2)}\n\n"
            
            # Generate response
            prompt = f"""
            {context_text}
            
            Generate a professional email response for:
            
            Original Email:
            Subject: {email.subject}
            From: {email.sender}
            Body: {email.body}
            
            Guidelines:
            - Be professional and helpful
            - Address the main points
            - Keep it concise (max {settings.max_response_length} words)
            - Use appropriate tone
            - Include relevant information from knowledge base if applicable
            
            Generate only the response body, no subject line.
            """
            
            response = openai.ChatCompletion.create(
                model=settings.default_ai_model,
                messages=[
                    {"role": "system", "content": "You are a professional email assistant. Generate helpful, concise responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.max_response_length * 2,
                temperature=settings.temperature
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Calculate confidence score (simple heuristic)
            confidence_score = self._calculate_confidence(email, response_text)
            
            return {
                "response_text": response_text,
                "confidence_score": confidence_score,
                "ai_model_used": settings.default_ai_model,
                "generated_at": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response_text": "Thank you for your email. I'll review it and get back to you soon.",
                "confidence_score": 0.3,
                "ai_model_used": settings.default_ai_model,
                "generated_at": datetime.now()
            }
    
    def _calculate_confidence(self, email: Email, response: str) -> float:
        """Calculate confidence score for generated response."""
        # Simple heuristic - in production, use more sophisticated methods
        confidence = 0.7  # Base confidence
        
        # Adjust based on response length
        if len(response) < 50:
            confidence -= 0.2
        elif len(response) > 300:
            confidence += 0.1
        
        # Adjust based on email complexity
        if len(email.body) > 1000:
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))


class EmailProcessor:
    """Main email processing orchestrator."""
    
    def __init__(self):
        self.analyzer = EmailAnalyzer()
        self.response_generator = ResponseGenerator()
    
    def process_email(self, email: Email) -> Dict[str, Any]:
        """Process email completely - analyze and generate response."""
        try:
            # Analyze email
            priority = self.analyzer.analyze_email_priority(email)
            key_info = self.analyzer.extract_key_information(email)
            
            # Generate response if needed
            response_data = None
            if key_info.get("requires_response", False) and settings.auto_respond_enabled:
                response_data = self.response_generator.generate_response(email, key_info)
            
            return {
                "priority": priority,
                "key_info": key_info,
                "response_data": response_data,
                "processed_at": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return {
                "priority": Priority.MEDIUM,
                "key_info": {},
                "response_data": None,
                "processed_at": datetime.now(),
                "error": str(e)
            }


# Global instances
email_processor = EmailProcessor()