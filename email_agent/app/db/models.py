from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from enum import Enum


class EmailStatus(str, Enum):
    """Email processing status."""
    UNREAD = "unread"
    READ = "read"
    PROCESSING = "processing"
    RESPONDED = "responded"
    FAILED = "failed"


class Priority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class EmailBase(SQLModel):
    """Base model for emails."""
    gmail_id: str = Field(unique=True, index=True)
    subject: str
    sender: str
    recipient: str
    body: str
    status: EmailStatus = Field(default=EmailStatus.UNREAD)
    priority: Priority = Field(default=Priority.MEDIUM)
    received_at: datetime
    processed_at: Optional[datetime] = None
    labels: Optional[str] = None  # JSON string of labels
    thread_id: Optional[str] = None


class Email(EmailBase, table=True):
    """Email model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    responses: List["EmailResponse"] = Relationship(back_populates="email")
    attachments: List["EmailAttachment"] = Relationship(back_populates="email")


class EmailResponseBase(SQLModel):
    """Base model for email responses."""
    email_id: int = Field(foreign_key="email.id")
    response_text: str
    generated_at: datetime
    sent_at: Optional[datetime] = None
    is_sent: bool = Field(default=False)
    ai_model_used: str
    confidence_score: Optional[float] = None


class EmailResponse(EmailResponseBase, table=True):
    """Email response model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    email: Email = Relationship(back_populates="responses")


class EmailAttachmentBase(SQLModel):
    """Base model for email attachments."""
    email_id: int = Field(foreign_key="email.id")
    filename: str
    file_size: int
    content_type: str
    file_path: Optional[str] = None
    attachment_id: str  # Gmail attachment ID


class EmailAttachment(EmailAttachmentBase, table=True):
    """Email attachment model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    email: Email = Relationship(back_populates="attachments")


class KnowledgeBaseBase(SQLModel):
    """Base model for knowledge base entries."""
    title: str
    content: str
    category: str
    tags: Optional[str] = None  # JSON string of tags
    created_at: datetime
    updated_at: datetime
    is_active: bool = Field(default=True)


class KnowledgeBase(KnowledgeBaseBase, table=True):
    """Knowledge base model."""
    id: Optional[int] = Field(default=None, primary_key=True)


class UserBase(SQLModel):
    """Base model for users."""
    email: str = Field(unique=True, index=True)
    full_name: str
    is_active: bool = Field(default=True)
    created_at: datetime
    last_login: Optional[datetime] = None


class User(UserBase, table=True):
    """User model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str


class ScheduledTaskBase(SQLModel):
    """Base model for scheduled tasks."""
    task_name: str
    task_type: str
    parameters: Optional[str] = None  # JSON string of parameters
    scheduled_for: datetime
    created_at: datetime
    executed_at: Optional[datetime] = None
    is_completed: bool = Field(default=False)
    is_active: bool = Field(default=True)
    error_message: Optional[str] = None


class ScheduledTask(ScheduledTaskBase, table=True):
    """Scheduled task model."""
    id: Optional[int] = Field(default=None, primary_key=True)