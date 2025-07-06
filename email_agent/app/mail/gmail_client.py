import base64
import os
import pickle
from typing import List, Dict, Optional, Any
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import logging
from ..core.config import settings


# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail client for email operations."""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Load existing token
        if os.path.exists(settings.token_path):
            with open(settings.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials are not valid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(settings.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {settings.credentials_path}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(settings.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self.service = build('gmail', 'v1', credentials=creds)
    
    def get_messages(self, query: str = 'is:unread', max_results: int = 10) -> List[Dict]:
        """Get Gmail messages based on query."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            detailed_messages = []
            
            for message in messages:
                msg_detail = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                detailed_messages.append(self._parse_message(msg_detail))
            
            return detailed_messages
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def _parse_message(self, message: Dict) -> Dict:
        """Parse Gmail message into structured format."""
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        recipient = next((h['value'] for h in headers if h['name'] == 'To'), '')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Parse date
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except:
            received_at = datetime.now()
        
        # Extract body
        body = self._extract_body(message['payload'])
        
        # Extract labels
        labels = message.get('labelIds', [])
        
        return {
            'gmail_id': message['id'],
            'thread_id': message.get('threadId'),
            'subject': subject,
            'sender': sender,
            'recipient': recipient,
            'body': body,
            'received_at': received_at,
            'labels': json.dumps(labels),
            'raw_message': message
        }
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract body text from message payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')
            elif payload['mimeType'] == 'text/html':
                if 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')
        
        return body
    
    def send_message(self, to: str, subject: str, body: str, 
                     reply_to_id: Optional[str] = None) -> Dict:
        """Send email message."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if reply_to_id:
                # Get original message for proper reply formatting
                original_msg = self.service.users().messages().get(
                    userId='me',
                    id=reply_to_id
                ).execute()
                
                # Set reply headers
                message['In-Reply-To'] = original_msg['id']
                message['References'] = original_msg['id']
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('ascii')
            
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Message sent successfully: {send_message['id']}")
            return send_message
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    def add_label(self, message_id: str, label_ids: List[str]) -> bool:
        """Add labels to message."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return False
    
    def get_attachments(self, message_id: str) -> List[Dict]:
        """Get message attachments."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()
            
            attachments = []
            payload = message['payload']
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['filename']:
                        attachment = {
                            'filename': part['filename'],
                            'attachment_id': part['body']['attachmentId'],
                            'size': part['body']['size'],
                            'mime_type': part['mimeType']
                        }
                        attachments.append(attachment)
            
            return attachments
            
        except Exception as e:
            logger.error(f"Error getting attachments: {e}")
            return []


# Global Gmail client instance
gmail_client = GmailClient()