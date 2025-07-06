#!/usr/bin/env python3
"""
Run script for Email Agent application.
This script starts the FastAPI server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Check if .env file exists
if not os.path.exists('.env'):
    print("Error: .env file not found. Please copy .env.example to .env and configure it.")
    sys.exit(1)

# Check if credentials.json exists
if not os.path.exists('credentials.json'):
    print("Warning: credentials.json not found. Gmail integration may not work.")

def main():
    """Main function to start the application."""
    print("Starting Email Agent API...")
    print("Access the API at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("System Status: http://localhost:8000/status")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nStopping Email Agent API...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()