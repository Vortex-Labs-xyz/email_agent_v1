#!/usr/bin/env python3
"""
Start script for the Email Agent server.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the Email Agent server."""
    print("Starting Email Agent Server...")
    print("=" * 40)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Check if virtual environment exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print("Virtual environment not found!")
        print("Please run setup.py first:")
        print("  python3 setup.py")
        return False
    
    # Determine the correct python path
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("Environment file (.env) not found!")
        print("Please copy .env.example to .env and configure your API keys.")
        return False
    
    # Start the server
    print("Starting server on http://localhost:8000")
    print("API documentation will be available at http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start uvicorn server
        cmd = [
            str(python_path), 
            "-m", "uvicorn", 
            "app.main:app", 
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]
        
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)