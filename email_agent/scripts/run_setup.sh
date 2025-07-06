#!/bin/bash

# Email Agent Setup Script
# This script sets up the Email Agent system

set -e

echo "=========================================="
echo "Email Agent Setup Script"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

echo "✓ Python 3 is installed"

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "✓ Python version: $python_version"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ .env file created from template"
        echo "⚠️  Please edit .env file with your configuration"
    else
        echo "Error: .env.example not found"
        exit 1
    fi
else
    echo "✓ .env file already exists"
fi

# Create credentials.json template
if [ ! -f "credentials.json" ]; then
    cat > credentials.json << 'EOF'
{
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
EOF
    echo "✓ credentials.json template created"
    echo "⚠️  Please update credentials.json with your Google API credentials"
else
    echo "✓ credentials.json already exists"
fi

# Create knowledge base directory
if [ ! -d "knowledge_base" ]; then
    mkdir -p knowledge_base
    
    # Create sample knowledge file
    cat > knowledge_base/sample_knowledge.txt << 'EOF'
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
EOF
    
    echo "✓ Knowledge base directory created with sample content"
else
    echo "✓ Knowledge base directory already exists"
fi

# Create data directory
mkdir -p data

echo ""
echo "=========================================="
echo "🎉 Email Agent Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update .env file with your actual API keys and configuration"
echo "2. Update credentials.json with your Google API credentials"
echo "3. Add knowledge base files to the knowledge_base/ directory"
echo "4. Start the application:"
echo "   source .venv/bin/activate"
echo "   python run.py"
echo "5. Access the API at http://localhost:8000"
echo "6. View documentation at http://localhost:8000/docs"
echo ""
echo "For help, see README.md or visit the documentation."
echo "=========================================="