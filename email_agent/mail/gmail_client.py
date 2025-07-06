import os
import base64
import email
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.logger import get_logger

logger = get_logger(__name__)

class GmailClient:
    """Gmail API client for email operations."""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._setup_credentials()
    
    def _setup_credentials(self) -> None:
        """Setup Gmail API credentials from environment variables."""
        try:
            # Get credentials from environment
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
            
            if not all([client_id, client_secret, refresh_token]):
                raise ValueError("Missing required Gmail credentials in environment")
            
            # Create credentials object
            self.credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=["https://www.googleapis.com/auth/gmail.modify"]
            )
            
            # Refresh token if needed
            if self.credentials.expired:
                self.credentials.refresh(Request())
            
            # Build service
            self.service = build("gmail", "v1", credentials=self.credentials)
            logger.info("Gmail API client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Gmail credentials: {e}")
            raise
    
    def fetch_unread(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with id, subject, sender, body, etc.
        """
        try:
            # Search for unread emails
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=max_results
            ).execute()
            
            messages = results.get("messages", [])
            
            if not messages:
                logger.info("No unread emails found")
                return []
            
            # Fetch full details for each message
            emails = []
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId="me",
                        id=message["id"],
                        format="full"
                    ).execute()
                    
                    email_data = self._parse_email(msg)
                    emails.append(email_data)
                    
                except HttpError as e:
                    logger.error(f"Error fetching message {message['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} unread emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            raise
    
    def _parse_email(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail API message to extract relevant information."""
        headers = msg["payload"].get("headers", [])
        
        # Extract headers
        subject = self._get_header_value(headers, "Subject")
        sender = self._get_header_value(headers, "From")
        date = self._get_header_value(headers, "Date")
        message_id = self._get_header_value(headers, "Message-ID")
        
        # Extract body
        body = self._extract_body(msg["payload"])
        
        return {
            "id": msg["id"],
            "thread_id": msg["threadId"],
            "subject": subject,
            "sender": sender,
            "date": date,
            "message_id": message_id,
            "body": body,
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", [])
        }
    
    def _get_header_value(self, headers: List[Dict], name: str) -> str:
        """Extract header value by name."""
        for header in headers:
            if header["name"].lower() == name.lower():
                return header["value"]
        return ""
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload."""
        body = ""
        
        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break
        else:
            # Single part message
            if payload["mimeType"] == "text/plain":
                data = payload["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
        
        return body
    
    def save_as_draft(self, to_email: str, subject: str, body: str, 
                     in_reply_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Save email as draft in Gmail.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            in_reply_to: Message ID for reply threading
            
        Returns:
            Draft information dictionary
        """
        try:
            # Create email message
            message = self._create_message(to_email, subject, body, in_reply_to)
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId="me",
                body={"message": message}
            ).execute()
            
            logger.info(f"Draft saved with ID: {draft['id']}")
            return {
                "draft_id": draft["id"],
                "message_id": draft["message"]["id"],
                "subject": subject,
                "to": to_email,
                "created_at": datetime.now().isoformat()
            }
            
        except HttpError as e:
            logger.error(f"Gmail API error saving draft: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving draft: {e}")
            raise
    
    def _create_message(self, to_email: str, subject: str, body: str, 
                       in_reply_to: Optional[str] = None) -> Dict[str, Any]:
        """Create email message dictionary."""
        # Create email headers
        headers = [
            {"name": "To", "value": to_email},
            {"name": "Subject", "value": subject}
        ]
        
        if in_reply_to:
            headers.append({"name": "In-Reply-To", "value": in_reply_to})
        
        # Create message payload
        message = {
            "payload": {
                "headers": headers,
                "body": {
                    "data": base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8")
                },
                "mimeType": "text/plain"
            }
        }
        
        return message
    
    def get_drafts(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get existing drafts from Gmail.
        
        Args:
            max_results: Maximum number of drafts to fetch
            
        Returns:
            List of draft dictionaries
        """
        try:
            # Get drafts list
            results = self.service.users().drafts().list(
                userId="me",
                maxResults=max_results
            ).execute()
            
            drafts = results.get("drafts", [])
            
            if not drafts:
                logger.info("No drafts found")
                return []
            
            # Fetch full details for each draft
            draft_details = []
            for draft in drafts:
                try:
                    draft_detail = self.service.users().drafts().get(
                        userId="me",
                        id=draft["id"]
                    ).execute()
                    
                    parsed_draft = self._parse_draft(draft_detail)
                    draft_details.append(parsed_draft)
                    
                except HttpError as e:
                    logger.error(f"Error fetching draft {draft['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(draft_details)} drafts")
            return draft_details
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching drafts: {e}")
            raise
    
    def _parse_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail API draft to extract relevant information."""
        message = draft["message"]
        headers = message["payload"].get("headers", [])
        
        # Extract headers
        subject = self._get_header_value(headers, "Subject")
        to_email = self._get_header_value(headers, "To")
        
        # Extract body
        body = self._extract_body(message["payload"])
        
        return {
            "draft_id": draft["id"],
            "message_id": message["id"],
            "subject": subject,
            "to": to_email,
            "body": body,
            "snippet": message.get("snippet", "")
        }
    
    def mark_as_read(self, message_id: str) -> None:
        """Mark email as read by removing UNREAD label."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            
            logger.info(f"Marked message {message_id} as read")
            
        except HttpError as e:
            logger.error(f"Error marking message as read: {e}")
            raise