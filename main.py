#!/usr/bin/env python3
"""
Email Agent v1 - Vortex Labs
Processes emails from Gmail, archives to S3, and logs to PostgreSQL
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import boto3
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import colorlog

# Load environment variables
load_dotenv()

# Configure logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

logger = colorlog.getLogger('email_agent')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class EmailAgent:
    """Main email processing agent"""
    
    def __init__(self):
        self.gmail_service = None
        self.s3_client = None
        self.db_conn = None
        self.setup_services()
    
    def setup_services(self):
        """Initialize all external services"""
        try:
            # Gmail setup
            self.setup_gmail()
            
            # AWS S3 setup
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'eu-central-1')
            )
            
            # PostgreSQL setup
            self.setup_database()
            
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            sys.exit(1)
    
    def setup_gmail(self):
        """Setup Gmail API connection"""
        creds = Credentials(
            token=None,
            refresh_token=os.getenv('GMAIL_REFRESH_TOKEN'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv('GMAIL_CLIENT_ID'),
            client_secret=os.getenv('GMAIL_CLIENT_SECRET'),
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        
        # Refresh the token
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("✅ Gmail API connected")
    
    def setup_database(self):
        """Setup PostgreSQL connection"""
        self.db_conn = psycopg2.connect(
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT', 5432),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD'),
            database=os.getenv('PGDATABASE')
        )
        
        # Create table if not exists
        with self.db_conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_archive (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    subject TEXT,
                    sender VARCHAR(255),
                    recipient VARCHAR(255),
                    date_received TIMESTAMP WITH TIME ZONE,
                    s3_key VARCHAR(500),
                    has_attachments BOOLEAN DEFAULT FALSE,
                    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    metadata JSONB
                )
            """)
            self.db_conn.commit()
        
        logger.info("✅ PostgreSQL connected and table ready")
    
    def fetch_unread_emails(self) -> List[Dict[str, Any]]:
        """Fetch unread emails from Gmail"""
        try:
            # Query for unread emails
            results = self.gmail_service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                # Get full message
                email_data = self.gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                emails.append(email_data)
                
                # Mark as read
                self.gmail_service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            
            logger.info(f"📧 Fetched {len(emails)} unread emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
    
    def parse_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email data into structured format"""
        headers = {h['name']: h['value'] 
                  for h in email_data['payload'].get('headers', [])}
        
        # Extract body
        body = self.extract_body(email_data['payload'])
        
        # Check for attachments
        has_attachments = self.has_attachments(email_data['payload'])
        
        parsed = {
            'message_id': email_data['id'],
            'thread_id': email_data['threadId'],
            'subject': headers.get('Subject', 'No Subject'),
            'sender': headers.get('From', ''),
            'recipient': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'has_attachments': has_attachments,
            'labels': email_data.get('labelIds', [])
        }
        
        return parsed
    
    def extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body += self.decode_base64(data)
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body']['data']
                    html = self.decode_base64(data)
                    body = BeautifulSoup(html, 'html.parser').get_text()
        else:
            if payload['body'].get('data'):
                body = self.decode_base64(payload['body']['data'])
        
        return body.strip()
    
    def decode_base64(self, data: str) -> str:
        """Decode base64 email data"""
        import base64
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    def has_attachments(self, payload: Dict[str, Any]) -> bool:
        """Check if email has attachments"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    return True
        return False
    
    def upload_to_s3(self, email_id: str, email_content: Dict[str, Any]) -> str:
        """Upload email to S3 and return the key"""
        # Generate S3 key with date hierarchy
        date = datetime.now(timezone.utc)
        s3_key = f"emails/{date.year}/{date.month:02d}/{date.day:02d}/{email_id}.json"
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=os.getenv('S3_BUCKET'),
            Key=s3_key,
            Body=json.dumps(email_content, indent=2, default=str),
            ContentType='application/json'
        )
        
        logger.info(f"☁️  Uploaded to S3: {s3_key}")
        return s3_key
    
    def save_to_database(self, email_data: Dict[str, Any], s3_key: str):
        """Save email metadata to PostgreSQL"""
        try:
            # Parse date
            from email.utils import parsedate_to_datetime
            date_received = parsedate_to_datetime(email_data['date'])
            
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO email_archive 
                    (message_id, subject, sender, recipient, date_received, 
                     s3_key, has_attachments, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                """, (
                    email_data['message_id'],
                    email_data['subject'],
                    email_data['sender'],
                    email_data['recipient'],
                    date_received,
                    s3_key,
                    email_data['has_attachments'],
                    json.dumps({
                        'thread_id': email_data['thread_id'],
                        'labels': email_data['labels']
                    })
                ))
                self.db_conn.commit()
            
            logger.info(f"💾 Saved to database: {email_data['message_id']}")
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            self.db_conn.rollback()
    
    def process_emails(self):
        """Main processing loop"""
        logger.info("🚀 Starting email processing...")
        
        # Fetch unread emails
        emails = self.fetch_unread_emails()
        
        if not emails:
            logger.info("No new emails to process")
            return
        
        # Process each email
        for email in emails:
            try:
                # Parse email
                parsed = self.parse_email(email)
                
                # Upload to S3
                s3_key = self.upload_to_s3(parsed['message_id'], parsed)
                
                # Save to database
                self.save_to_database(parsed, s3_key)
                
                logger.info(f"✅ Processed: {parsed['subject']}")
                
            except Exception as e:
                logger.error(f"Failed to process email: {e}")
                continue
        
        logger.info(f"✨ Processed {len(emails)} emails successfully")
    
    def cleanup(self):
        """Cleanup connections"""
        if self.db_conn:
            self.db_conn.close()
        logger.info("👋 Cleanup completed")


def main():
    """Main entry point"""
    try:
        agent = EmailAgent()
        agent.process_emails()
    except KeyboardInterrupt:
        logger.info("⚠️  Process interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.cleanup()


if __name__ == "__main__":
    main() 