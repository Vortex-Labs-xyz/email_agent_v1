from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, Any, Optional, List
from ..core.config import settings
from ..mail.gmail_client import gmail_client
from ..db.models import Email, EmailStatus, ScheduledTask
from ..db.database import async_session
from .ai_agent import email_processor
from sqlmodel import select

logger = logging.getLogger(__name__)


class EmailScheduler:
    """Scheduler for automated email processing tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Set up scheduled jobs."""
        # Email checking job
        self.scheduler.add_job(
            self.process_new_emails,
            IntervalTrigger(seconds=settings.email_check_interval),
            id='email_checker',
            name='Check for new emails',
            replace_existing=True
        )
        
        # Database cleanup job (daily)
        self.scheduler.add_job(
            self.cleanup_old_data,
            CronTrigger(hour=2, minute=0),  # Run at 2 AM daily
            id='cleanup_job',
            name='Clean up old data',
            replace_existing=True
        )
        
        # Knowledge base update job (weekly)
        self.scheduler.add_job(
            self.update_knowledge_base,
            CronTrigger(day_of_week='sun', hour=3, minute=0),  # Run Sunday at 3 AM
            id='knowledge_update',
            name='Update knowledge base',
            replace_existing=True
        )
    
    async def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Email scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Email scheduler stopped")
    
    async def process_new_emails(self):
        """Process new emails from Gmail."""
        try:
            logger.info("Starting email processing cycle")
            
            # Get new emails from Gmail
            messages = gmail_client.get_messages(
                query='is:unread',
                max_results=settings.max_emails_per_batch
            )
            
            if not messages:
                logger.info("No new emails to process")
                return
            
            logger.info(f"Found {len(messages)} new emails")
            
            # Process each email
            for message_data in messages:
                try:
                    await self._process_single_email(message_data)
                except Exception as e:
                    logger.error(f"Error processing email {message_data.get('gmail_id')}: {e}")
            
            logger.info("Email processing cycle completed")
            
        except Exception as e:
            logger.error(f"Error in email processing cycle: {e}")
    
    async def _process_single_email(self, message_data: Dict):
        """Process a single email."""
        async with async_session() as session:
            try:
                # Check if email already exists
                existing_email = await session.exec(
                    select(Email).where(Email.gmail_id == message_data['gmail_id'])
                )
                existing_email = existing_email.first()
                
                if existing_email:
                    logger.info(f"Email {message_data['gmail_id']} already processed")
                    return
                
                # Create new email record
                email = Email(
                    gmail_id=message_data['gmail_id'],
                    thread_id=message_data['thread_id'],
                    subject=message_data['subject'],
                    sender=message_data['sender'],
                    recipient=message_data['recipient'],
                    body=message_data['body'],
                    received_at=message_data['received_at'],
                    labels=message_data['labels'],
                    status=EmailStatus.PROCESSING
                )
                
                session.add(email)
                await session.commit()
                await session.refresh(email)
                
                # Process with AI agent
                processing_result = email_processor.process_email(email)
                
                # Update email with processing results
                email.status = EmailStatus.READ
                email.priority = processing_result['priority']
                email.processed_at = processing_result['processed_at']
                
                # Generate response if needed
                if processing_result.get('response_data'):
                    response_data = processing_result['response_data']
                    
                    # Create email response record
                    email_response = EmailResponse(
                        email_id=email.id,
                        response_text=response_data['response_text'],
                        generated_at=response_data['generated_at'],
                        ai_model_used=response_data['ai_model_used'],
                        confidence_score=response_data.get('confidence_score', 0.7)
                    )
                    
                    session.add(email_response)
                    
                    # Send response if confidence is high enough
                    if email_response.confidence_score >= 0.8:
                        try:
                            sent_message = gmail_client.send_message(
                                to=email.sender,
                                subject=f"Re: {email.subject}",
                                body=email_response.response_text,
                                reply_to_id=email.gmail_id
                            )
                            
                            if sent_message:
                                email_response.is_sent = True
                                email_response.sent_at = datetime.now()
                                email.status = EmailStatus.RESPONDED
                                
                                logger.info(f"Auto-response sent for email {email.gmail_id}")
                        
                        except Exception as e:
                            logger.error(f"Error sending auto-response: {e}")
                
                # Mark as read in Gmail
                gmail_client.mark_as_read(email.gmail_id)
                
                await session.commit()
                
                logger.info(f"Successfully processed email {email.gmail_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing email: {e}")
                raise
    
    async def cleanup_old_data(self):
        """Clean up old processed emails and responses."""
        try:
            logger.info("Starting data cleanup")
            
            # Delete old processed emails (older than 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            
            async with async_session() as session:
                # Delete old emails
                old_emails = await session.exec(
                    select(Email).where(
                        Email.processed_at < cutoff_date,
                        Email.status != EmailStatus.URGENT
                    )
                )
                
                count = 0
                for email in old_emails:
                    await session.delete(email)
                    count += 1
                
                await session.commit()
                logger.info(f"Cleaned up {count} old emails")
                
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def update_knowledge_base(self):
        """Update knowledge base with recent email interactions."""
        try:
            logger.info("Starting knowledge base update")
            
            # Get recent successful email interactions
            week_ago = datetime.now() - timedelta(days=7)
            
            async with async_session() as session:
                recent_emails = await session.exec(
                    select(Email).where(
                        Email.processed_at >= week_ago,
                        Email.status == EmailStatus.RESPONDED
                    )
                )
                
                from .knowledge_base import knowledge_base_manager
                
                count = 0
                for email in recent_emails:
                    # Get the response
                    responses = await session.exec(
                        select(EmailResponse).where(
                            EmailResponse.email_id == email.id,
                            EmailResponse.is_sent == True
                        )
                    )
                    
                    response = responses.first()
                    if response:
                        knowledge_base_manager.add_email_context(
                            email.subject,
                            email.body,
                            response.response_text
                        )
                        count += 1
                
                logger.info(f"Updated knowledge base with {count} email interactions")
                
        except Exception as e:
            logger.error(f"Error updating knowledge base: {e}")
    
    def add_scheduled_task(self, task_name: str, task_function, 
                          trigger, **kwargs) -> str:
        """Add a custom scheduled task."""
        try:
            job = self.scheduler.add_job(
                task_function,
                trigger,
                name=task_name,
                **kwargs
            )
            
            logger.info(f"Added scheduled task: {task_name}")
            return job.id
            
        except Exception as e:
            logger.error(f"Error adding scheduled task: {e}")
            return None
    
    def remove_scheduled_task(self, job_id: str) -> bool:
        """Remove a scheduled task."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled task: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing scheduled task: {e}")
            return False
    
    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return jobs


# Global scheduler instance
email_scheduler = EmailScheduler()