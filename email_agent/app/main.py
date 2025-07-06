import os
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from ..mail.gmail_client import GmailClient
from ..agent.processor import EmailProcessor
from ..core.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Global instances
gmail_client = None
email_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global gmail_client, email_processor
    
    try:
        # Initialize clients
        logger.info("Initializing email agent services...")
        gmail_client = GmailClient()
        email_processor = EmailProcessor()
        logger.info("Email agent services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        logger.info("Shutting down email agent services...")

# Create FastAPI app
app = FastAPI(
    title="Email Agent API",
    description="Intelligent email processing system with AI-powered categorization and response generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    services: Dict[str, str] = Field(default_factory=dict)

class EmailProcessingRequest(BaseModel):
    max_emails: int = Field(default=10, ge=1, le=50)
    mark_as_read: bool = Field(default=False)

class EmailProcessingResponse(BaseModel):
    processed_count: int
    drafts_created: int
    emails_processed: List[Dict[str, Any]]
    processing_time: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class DraftInfo(BaseModel):
    draft_id: str
    message_id: str
    subject: str
    to: str
    created_at: str

# API Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        services = {}
        
        # Check Gmail client
        if gmail_client:
            try:
                # Try to get service info
                gmail_client.service.users().getProfile(userId="me").execute()
                services["gmail"] = "connected"
            except Exception as e:
                services["gmail"] = f"error: {str(e)}"
        else:
            services["gmail"] = "not_initialized"
        
        # Check OpenAI client
        if email_processor and email_processor.client:
            services["openai"] = "connected"
        else:
            services["openai"] = "not_initialized"
        
        return HealthResponse(services=services)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/emails/process-and-save-drafts", response_model=EmailProcessingResponse)
async def process_emails_and_save_drafts(
    request: EmailProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Process unread emails and save AI-generated responses as drafts.
    
    This endpoint:
    1. Fetches unread emails from Gmail
    2. Processes each email with AI (categorization + response generation)
    3. Saves appropriate responses as Gmail drafts
    4. Optionally marks emails as read
    """
    if not gmail_client or not email_processor:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    start_time = datetime.now()
    
    try:
        # Fetch unread emails
        logger.info(f"Fetching up to {request.max_emails} unread emails...")
        emails = gmail_client.fetch_unread(max_results=request.max_emails)
        
        if not emails:
            return EmailProcessingResponse(
                processed_count=0,
                drafts_created=0,
                emails_processed=[],
                processing_time=0.0
            )
        
        processed_emails = []
        drafts_created = 0
        
        # Process each email
        for email_data in emails:
            try:
                logger.info(f"Processing email: {email_data['subject'][:50]}...")
                
                # Process email with AI
                processing_result = email_processor.categorize_and_process_email(
                    email_data['body'],
                    email_data['sender']
                )
                
                # Extract sender email address
                sender_email = email_data['sender']
                if '<' in sender_email:
                    sender_email = sender_email.split('<')[1].split('>')[0]
                
                # Create draft if response is needed
                draft_info = None
                if processing_result['response_type'] in ['reply', 'new']:
                    # Generate subject for reply
                    subject = email_data['subject']
                    if not subject.lower().startswith('re:'):
                        subject = f"Re: {subject}"
                    
                    # Save as draft
                    draft_info = gmail_client.save_as_draft(
                        to_email=sender_email,
                        subject=subject,
                        body=processing_result['response'],
                        in_reply_to=email_data.get('message_id')
                    )
                    drafts_created += 1
                
                # Mark as read if requested
                if request.mark_as_read:
                    background_tasks.add_task(
                        gmail_client.mark_as_read,
                        email_data['id']
                    )
                
                # Compile processed email info
                processed_email = {
                    "original_email": {
                        "id": email_data['id'],
                        "subject": email_data['subject'],
                        "sender": email_data['sender'],
                        "date": email_data['date'],
                        "snippet": email_data['snippet']
                    },
                    "processing_result": processing_result,
                    "draft_info": draft_info
                }
                
                processed_emails.append(processed_email)
                
            except Exception as e:
                logger.error(f"Error processing email {email_data['id']}: {e}")
                # Continue processing other emails
                continue
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Successfully processed {len(processed_emails)} emails, created {drafts_created} drafts")
        
        return EmailProcessingResponse(
            processed_count=len(processed_emails),
            drafts_created=drafts_created,
            emails_processed=processed_emails,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing emails: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing emails: {str(e)}")

@app.get("/emails/drafts")
async def get_drafts(max_results: int = 10):
    """Get existing drafts from Gmail."""
    if not gmail_client:
        raise HTTPException(status_code=500, detail="Gmail client not initialized")
    
    try:
        drafts = gmail_client.get_drafts(max_results=max_results)
        
        return {
            "drafts": drafts,
            "count": len(drafts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching drafts: {str(e)}")

@app.get("/emails/unread")
async def get_unread_emails(max_results: int = 10):
    """Get unread emails without processing them."""
    if not gmail_client:
        raise HTTPException(status_code=500, detail="Gmail client not initialized")
    
    try:
        emails = gmail_client.fetch_unread(max_results=max_results)
        
        return {
            "emails": emails,
            "count": len(emails),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching unread emails: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching unread emails: {str(e)}")

@app.post("/emails/categorize")
async def categorize_email(email_text: str, sender: str):
    """Categorize a single email without saving drafts."""
    if not email_processor:
        raise HTTPException(status_code=500, detail="Email processor not initialized")
    
    try:
        result = email_processor.categorize_and_process_email(email_text, sender)
        return result
        
    except Exception as e:
        logger.error(f"Error categorizing email: {e}")
        raise HTTPException(status_code=500, detail=f"Error categorizing email: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)