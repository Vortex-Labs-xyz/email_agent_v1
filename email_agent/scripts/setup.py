#!/usr/bin/env python3
"""
Setup script for Email Agent system.
This script helps with initial setup and configuration.
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def run_command(command, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        return None


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required.")
        sys.exit(1)
    print(f"✓ Python version {sys.version.split()[0]} is compatible")


def create_virtual_environment():
    """Create virtual environment if it doesn't exist."""
    if not os.path.exists(".venv"):
        print("Creating virtual environment...")
        result = run_command("python -m venv .venv")
        if result is None:
            print("Error creating virtual environment")
            sys.exit(1)
        print("✓ Virtual environment created")
    else:
        print("✓ Virtual environment already exists")


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    # Determine pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = ".venv\\Scripts\\pip"
    else:  # Unix-like
        pip_path = ".venv/bin/pip"
    
    # Upgrade pip
    run_command(f"{pip_path} install --upgrade pip")
    
    # Install dependencies
    result = run_command(f"{pip_path} install -r requirements.txt")
    if result is None:
        print("Error installing dependencies")
        sys.exit(1)
    print("✓ Dependencies installed")


def create_env_file():
    """Create .env file from template."""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("Creating .env file from template...")
            run_command("cp .env.example .env")
            print("✓ .env file created")
            print("⚠️  Please edit .env file with your configuration")
        else:
            print("Error: .env.example not found")
            sys.exit(1)
    else:
        print("✓ .env file already exists")


def check_environment_variables():
    """Check if required environment variables are set."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "OPENAI_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing or default environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("Please update your .env file with actual values")
        return False
    
    print("✓ All required environment variables are set")
    return True


def initialize_database():
    """Initialize the database."""
    print("Initializing database...")
    
    # Determine python path
    if os.name == 'nt':  # Windows
        python_path = ".venv\\Scripts\\python"
    else:  # Unix-like
        python_path = ".venv/bin/python"
    
    # Initialize database
    init_script = """
import asyncio
import sys
sys.path.append('.')
from app.db.database import init_db

async def main():
    await init_db()
    print("Database initialized successfully")

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    with open("temp_init_db.py", "w") as f:
        f.write(init_script)
    
    result = run_command(f"{python_path} temp_init_db.py")
    os.remove("temp_init_db.py")
    
    if result is None:
        print("Error initializing database")
        return False
    
    print("✓ Database initialized")
    return True


def create_credentials_template():
    """Create credentials.json template."""
    if not os.path.exists("credentials.json"):
        credentials_template = {
            "installed": {
                "client_id": "your_client_id_here",
                "project_id": "your_project_id_here",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "your_client_secret_here",
                "redirect_uris": ["http://localhost:8000/auth/callback"]
            }
        }
        
        with open("credentials.json", "w") as f:
            json.dump(credentials_template, f, indent=2)
        
        print("✓ credentials.json template created")
        print("⚠️  Please update credentials.json with your Google API credentials")
    else:
        print("✓ credentials.json already exists")


def create_knowledge_base_directory():
    """Create knowledge base directory."""
    kb_dir = Path("knowledge_base")
    if not kb_dir.exists():
        kb_dir.mkdir(exist_ok=True)
        print("✓ Knowledge base directory created")
        
        # Create sample knowledge file
        sample_content = """
# Email Agent Knowledge Base

## Common Responses

### Meeting Requests
When someone requests a meeting, acknowledge the request and suggest available time slots.

### Technical Support
For technical issues, gather information about the problem and provide initial troubleshooting steps.

### General Inquiries
For general questions, provide helpful information and offer to assist further if needed.

## Contact Information

- Support Email: support@company.com
- Phone: (555) 123-4567
- Office Hours: Monday-Friday, 9 AM - 5 PM
"""
        
        with open(kb_dir / "sample_knowledge.txt", "w") as f:
            f.write(sample_content)
        
        print("✓ Sample knowledge base file created")
    else:
        print("✓ Knowledge base directory already exists")


def print_next_steps():
    """Print next steps for the user."""
    print("\n" + "="*60)
    print("🎉 Email Agent Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update .env file with your actual API keys and configuration")
    print("2. Update credentials.json with your Google API credentials")
    print("3. Add knowledge base files to the knowledge_base/ directory")
    print("4. Start the application:")
    print("   - Activate virtual environment:")
    if os.name == 'nt':
        print("     .venv\\Scripts\\activate")
    else:
        print("     source .venv/bin/activate")
    print("   - Run the application:")
    print("     python -m uvicorn app.main:app --reload")
    print("5. Access the API at http://localhost:8000")
    print("6. View documentation at http://localhost:8000/docs")
    print("\nFor help, see README.md or visit the documentation.")


def main():
    """Main setup function."""
    print("Email Agent Setup Script")
    print("="*40)
    
    # Check Python version
    check_python_version()
    
    # Create virtual environment
    create_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Create configuration files
    create_env_file()
    create_credentials_template()
    
    # Create directories
    create_knowledge_base_directory()
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Initialize database (only if environment is properly configured)
    if env_ok:
        db_ok = initialize_database()
        if not db_ok:
            print("⚠️  Database initialization failed. Please check your configuration.")
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main()