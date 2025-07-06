from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlmodel import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..db.database import get_session
from ..db.models import Email, EmailResponse, EmailStatus, Priority
from ..agent.ai_agent import email_processor
from ..mail.gmail_client import gmail_client
from ..agent.scheduler import email_scheduler
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[EmailStatus] = None,
    priority: Optional[Priority] = None,
    sender: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get emails with optional filtering."""
    try:
        query = select(Email)
        
        # Apply filters
        if status:
            query = query.where(Email.status == status)
        if priority:
            query = query.where(Email.priority == priority)
        if sender:
            query = query.where(Email.sender.contains(sender))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.exec(query)
        emails = result.all()
        
        return [
            {
                "id": email.id,
                "gmail_id": email.gmail_id,
                "subject": email.subject,
                "sender": email.sender,
                "recipient": email.recipient,
                "status": email.status,
                "priority": email.priority,
                "received_at": email.received_at.isoformat(),
                "processed_at": email.processed_at.isoformat() if email.processed_at else None,
                "labels": email.labels
            }
            for email in emails
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving emails: {str(e)}"
        )


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific email by ID."""
    try:
        email = await session.get(Email, email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # Get responses
        responses_query = select(EmailResponse).where(EmailResponse.email_id == email_id)
        responses_result = await session.exec(responses_query)
        responses = responses_result.all()
        
        return {
            "id": email.id,
            "gmail_id": email.gmail_id,
            "thread_id": email.thread_id,
            "subject": email.subject,
            "sender": email.sender,
            "recipient": email.recipient,
            "body": email.body,
            "status": email.status,
            "priority": email.priority,
            "received_at": email.received_at.isoformat(),
            "processed_at": email.processed_at.isoformat() if email.processed_at else None,
            "labels": email.labels,
            "responses": [
                {
                    "id": response.id,
                    "response_text": response.response_text,
                    "generated_at": response.generated_at.isoformat(),
                    "sent_at": response.sent_at.isoformat() if response.sent_at else None,
                    "is_sent": response.is_sent,
                    "confidence_score": response.confidence_score,
                    "ai_model_used": response.ai_model_used
                }
                for response in responses
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving email: {str(e)}"
        )


@router.post("/sync")
async def sync_emails():
    """Manually trigger email synchronization."""
    try:
        await email_scheduler.process_new_emails()
        return {"message": "Email synchronization completed"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing emails: {str(e)}"
        )


@router.post("/{email_id}/generate-response")
async def generate_response(
    email_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Generate AI response for a specific email."""
    try:
        email = await session.get(Email, email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # Generate response
        processing_result = email_processor.process_email(email)
        
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
            await session.commit()
            await session.refresh(email_response)
            
            return {
                "id": email_response.id,
                "response_text": email_response.response_text,
                "confidence_score": email_response.confidence_score,
                "generated_at": email_response.generated_at.isoformat(),
                "ai_model_used": email_response.ai_model_used
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not generate response for this email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )


@router.post("/{email_id}/send-response/{response_id}")
async def send_response(
    email_id: int,
    response_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Send a generated response."""
    try:
        email = await session.get(Email, email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        response = await session.get(EmailResponse, response_id)
        if not response or response.email_id != email_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )
        
        if response.is_sent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response already sent"
            )
        
        # Send the response
        sent_message = gmail_client.send_message(
            to=email.sender,
            subject=f"Re: {email.subject}",
            body=response.response_text,
            reply_to_id=email.gmail_id
        )
        
        if sent_message:
            response.is_sent = True
            response.sent_at = datetime.now()
            email.status = EmailStatus.RESPONDED
            
            await session.commit()
            
            return {
                "message": "Response sent successfully",
                "gmail_message_id": sent_message.get('id')
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send response"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending response: {str(e)}"
        )


@router.put("/{email_id}/status")
async def update_email_status(
    email_id: int,
    new_status: EmailStatus,
    session: AsyncSession = Depends(get_session)
):
    """Update email status."""
    try:
        email = await session.get(Email, email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        email.status = new_status
        await session.commit()
        
        return {"message": "Email status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating email status: {str(e)}"
        )


@router.put("/{email_id}/priority")
async def update_email_priority(
    email_id: int,
    new_priority: Priority,
    session: AsyncSession = Depends(get_session)
):
    """Update email priority."""
    try:
        email = await session.get(Email, email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        email.priority = new_priority
        await session.commit()
        
        return {"message": "Email priority updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating email priority: {str(e)}"
        )


@router.get("/stats/dashboard")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session)
):
    """Get dashboard statistics."""
    try:
        # Get email counts by status
        total_emails = await session.exec(select(Email))
        all_emails = total_emails.all()
        
        status_counts = {}
        priority_counts = {}
        
        for email in all_emails:
            status_counts[email.status] = status_counts.get(email.status, 0) + 1
            priority_counts[email.priority] = priority_counts.get(email.priority, 0) + 1
        
        # Get recent activity
        recent_date = datetime.now() - timedelta(days=7)
        recent_emails = await session.exec(
            select(Email).where(Email.received_at >= recent_date)
        )
        
        # Get response stats
        responses_query = select(EmailResponse)
        responses_result = await session.exec(responses_query)
        all_responses = responses_result.all()
        
        response_stats = {
            "total_responses": len(all_responses),
            "sent_responses": len([r for r in all_responses if r.is_sent]),
            "average_confidence": sum([r.confidence_score or 0 for r in all_responses]) / len(all_responses) if all_responses else 0
        }
        
        return {
            "total_emails": len(all_emails),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "recent_emails": len(recent_emails.all()),
            "response_stats": response_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard stats: {str(e)}"
        )