import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from openai import OpenAI

from ..core.logger import get_logger

logger = get_logger(__name__)

class EmailProcessor:
    """AI-powered email processor for categorization and response generation."""
    
    def __init__(self):
        self.client = None
        self.model = "gpt-4o"
        self._setup_openai_client()
    
    def _setup_openai_client(self) -> None:
        """Setup OpenAI client from environment variables."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY in environment")
            
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
            raise
    
    def categorize_and_process_email(self, email_text: str, sender: str) -> Dict[str, Any]:
        """
        Categorize email and generate appropriate response.
        
        Args:
            email_text: The email content to process
            sender: Email sender address
            
        Returns:
            Dictionary containing category, priority, response, and metadata
        """
        try:
            # First, categorize the email
            category_result = self._categorize_email(email_text, sender)
            
            # Generate response based on category
            response_result = self._generate_response(
                email_text, 
                sender, 
                category_result["category"],
                category_result["priority"]
            )
            
            # Combine results
            result = {
                "category": category_result["category"],
                "priority": category_result["priority"],
                "confidence": category_result["confidence"],
                "keywords": category_result["keywords"],
                "response": response_result["response"],
                "response_type": response_result["response_type"],
                "suggested_actions": response_result["suggested_actions"],
                "processed_at": datetime.now().isoformat(),
                "sender": sender
            }
            
            logger.info(f"Successfully processed email from {sender} - Category: {result['category']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            raise
    
    def _categorize_email(self, email_text: str, sender: str) -> Dict[str, Any]:
        """Categorize email using AI."""
        prompt = f"""
        Analyze this email and categorize it. Return your analysis in JSON format.
        
        Email from: {sender}
        Email content: {email_text}
        
        Please categorize this email into one of these categories:
        - business: Business inquiries, partnerships, work-related
        - personal: Personal messages from friends/family
        - support: Technical support requests, bug reports
        - sales: Sales inquiries, product questions
        - invoice: Invoices, billing, payment-related
        - newsletter: Newsletters, marketing emails
        - spam: Spam or unwanted emails
        - urgent: Urgent matters requiring immediate attention
        - other: Anything that doesn't fit above categories
        
        Also assign a priority level (1-5, where 5 is highest priority).
        
        Return a JSON object with:
        {{
            "category": "category_name",
            "priority": 1-5,
            "confidence": 0.0-1.0,
            "keywords": ["keyword1", "keyword2"],
            "reasoning": "Brief explanation of categorization"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback if JSON parsing fails
                return {
                    "category": "other",
                    "priority": 3,
                    "confidence": 0.5,
                    "keywords": [],
                    "reasoning": "Failed to parse AI response"
                }
                
        except Exception as e:
            logger.error(f"Error categorizing email: {e}")
            return {
                "category": "other",
                "priority": 3,
                "confidence": 0.0,
                "keywords": [],
                "reasoning": f"Error: {str(e)}"
            }
    
    def _generate_response(self, email_text: str, sender: str, 
                          category: str, priority: int) -> Dict[str, Any]:
        """Generate appropriate response based on email category."""
        
        # Define response templates based on category
        response_templates = {
            "business": "professional business response",
            "personal": "friendly personal response",
            "support": "helpful technical support response",
            "sales": "informative sales response",
            "invoice": "acknowledgment of invoice/billing",
            "newsletter": "unsubscribe or acknowledgment",
            "spam": "no response needed",
            "urgent": "immediate attention response",
            "other": "general polite response"
        }
        
        response_style = response_templates.get(category, "general polite response")
        
        prompt = f"""
        Generate a professional email response for this email. The response should be a {response_style}.
        
        Original email from: {sender}
        Email category: {category}
        Priority level: {priority}
        
        Original email content:
        {email_text}
        
        Please generate:
        1. A professional email response (keep it concise but appropriate)
        2. Suggest any follow-up actions needed
        3. Determine if this is a reply, new email, or no response needed
        
        Return a JSON object with:
        {{
            "response": "The email response text",
            "response_type": "reply|new|none",
            "suggested_actions": ["action1", "action2"],
            "tone": "professional|friendly|urgent|formal"
        }}
        
        Guidelines:
        - Keep responses concise but complete
        - Match the tone to the email category
        - For spam/newsletters, response_type should be "none"
        - For urgent emails, include clear next steps
        - Always be professional and helpful
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.4
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback response
                return {
                    "response": "Thank you for your email. I'll review it and get back to you shortly.",
                    "response_type": "reply",
                    "suggested_actions": ["Review email content", "Respond within 24 hours"],
                    "tone": "professional"
                }
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "Thank you for your email. I'll review it and get back to you shortly.",
                "response_type": "reply",
                "suggested_actions": ["Review email content", "Manual response needed"],
                "tone": "professional"
            }
    
    def extract_invoice_info(self, email_text: str) -> Optional[Dict[str, Any]]:
        """Extract invoice information from email content."""
        try:
            prompt = f"""
            Analyze this email for invoice/billing information. Extract structured data if this appears to be an invoice or billing-related email.
            
            Email content:
            {email_text}
            
            If this is an invoice/billing email, extract:
            - Invoice number
            - Amount
            - Due date
            - Vendor/Company
            - Description/Items
            
            Return JSON with extracted information, or null if not an invoice.
            
            {{
                "is_invoice": true/false,
                "invoice_number": "string or null",
                "amount": "string or null",
                "currency": "string or null",
                "due_date": "string or null",
                "vendor": "string or null",
                "description": "string or null"
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
                return result if result.get("is_invoice") else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting invoice info: {e}")
            return None
    
    def generate_task_suggestions(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate task suggestions based on email content."""
        try:
            prompt = f"""
            Based on this email analysis, suggest specific tasks that should be created.
            
            Email category: {email_data['category']}
            Priority: {email_data['priority']}
            Sender: {email_data['sender']}
            Suggested actions: {email_data['suggested_actions']}
            
            Generate 1-3 specific, actionable tasks. Each task should have:
            - Clear title
            - Description
            - Priority level
            - Due date suggestion
            
            Return JSON array:
            [
                {{
                    "title": "Task title",
                    "description": "Task description",
                    "priority": 1-4,
                    "due_date": "YYYY-MM-DD or null",
                    "project": "suggested project name or null"
                }}
            ]
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            
            if json_match:
                tasks = json.loads(json_match.group())
                return tasks
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating task suggestions: {e}")
            return []