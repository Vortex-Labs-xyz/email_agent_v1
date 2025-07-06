#!/usr/bin/env python3
"""
Gmail OAuth2 Token Generation Script

This script helps users generate the necessary OAuth2 tokens for Gmail API access.
Run this script to authenticate with Gmail and generate the refresh token needed
for the email agent system.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

def get_credentials_from_env() -> Dict[str, str]:
    """Get OAuth2 credentials from environment or user input."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id:
        print("Google Client ID not found in environment.")
        client_id = input("Enter your Google Client ID: ").strip()
    
    if not client_secret:
        print("Google Client Secret not found in environment.")
        client_secret = input("Enter your Google Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("ERROR: Both Client ID and Client Secret are required.")
        sys.exit(1)
    
    return {
        "client_id": client_id,
        "client_secret": client_secret
    }

def create_credentials_file(client_id: str, client_secret: str) -> str:
    """Create temporary credentials file for OAuth flow."""
    credentials_data = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/", "urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    credentials_file = "temp_credentials.json"
    with open(credentials_file, 'w') as f:
        json.dump(credentials_data, f)
    
    return credentials_file

def authenticate_gmail() -> Credentials:
    """Authenticate with Gmail and return credentials."""
    print("Starting Gmail OAuth2 authentication...")
    
    # Get credentials from environment or user input
    creds_info = get_credentials_from_env()
    
    # Create temporary credentials file
    credentials_file = create_credentials_file(
        creds_info["client_id"], 
        creds_info["client_secret"]
    )
    
    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, SCOPES
        )
        
        print("\nStarting OAuth2 flow...")
        print("A web browser will open for authentication.")
        print("Please complete the authentication process in your browser.")
        
        # This will open a browser window for authentication
        creds = flow.run_local_server(port=8080)
        
        return creds
        
    finally:
        # Clean up temporary file
        if os.path.exists(credentials_file):
            os.remove(credentials_file)

def test_gmail_connection(creds: Credentials) -> bool:
    """Test Gmail API connection with the provided credentials."""
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Test by getting user profile
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"✓ Successfully connected to Gmail for: {profile.get('emailAddress')}")
        
        # Test by listing a few messages
        messages = service.users().messages().list(userId='me', maxResults=1).execute()
        print(f"✓ Gmail API is working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Gmail API test failed: {e}")
        return False

def save_tokens_to_env(creds: Credentials, client_id: str, client_secret: str) -> None:
    """Save tokens to .env file."""
    env_file = Path(".env")
    env_content = []
    
    # Read existing .env file if it exists
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                # Skip existing Gmail-related lines
                if not any(line.startswith(key) for key in [
                    'GOOGLE_CLIENT_ID=',
                    'GOOGLE_CLIENT_SECRET=',
                    'GMAIL_REFRESH_TOKEN='
                ]):
                    env_content.append(line.rstrip())
    
    # Add Gmail credentials
    env_content.extend([
        f"GOOGLE_CLIENT_ID={client_id}",
        f"GOOGLE_CLIENT_SECRET={client_secret}",
        f"GMAIL_REFRESH_TOKEN={creds.refresh_token}"
    ])
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(env_content) + '\n')
    
    print(f"✓ Tokens saved to {env_file}")

def main():
    """Main function to run the OAuth2 token generation process."""
    print("Gmail OAuth2 Token Generation")
    print("=" * 40)
    print()
    
    print("This script will help you generate OAuth2 tokens for Gmail API access.")
    print("You'll need:")
    print("1. Google Cloud Project with Gmail API enabled")
    print("2. OAuth2 Client ID and Client Secret")
    print("3. Web browser for authentication")
    print()
    
    # Check if we're in the right directory
    if not Path("email_agent").exists():
        print("ERROR: This script should be run from the project root directory.")
        print("Make sure you're in the directory containing the 'email_agent' folder.")
        sys.exit(1)
    
    try:
        # Authenticate with Gmail
        creds = authenticate_gmail()
        
        if not creds or not creds.refresh_token:
            print("ERROR: Failed to obtain refresh token.")
            print("Make sure you completed the authentication process.")
            sys.exit(1)
        
        # Test the connection
        if not test_gmail_connection(creds):
            print("ERROR: Gmail API connection test failed.")
            sys.exit(1)
        
        # Save tokens to .env file
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id:
            client_id = input("Enter your Google Client ID to save: ").strip()
        if not client_secret:
            client_secret = input("Enter your Google Client Secret to save: ").strip()
        
        save_tokens_to_env(creds, client_id, client_secret)
        
        print("\n" + "=" * 40)
        print("SUCCESS! Gmail OAuth2 setup completed.")
        print("You can now use the email agent system.")
        print("=" * 40)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()