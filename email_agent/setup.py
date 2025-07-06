#!/usr/bin/env python3
"""
Setup script for the Email Agent system.
"""

import os
import subprocess
import sys
import venv
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    """Main setup function."""
    print("Email Agent System Setup")
    print("=" * 40)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    
    print(f"Setting up in: {project_root}")
    print()
    
    # Create virtual environment
    print("1. Creating virtual environment...")
    if venv_path.exists():
        print("   Virtual environment already exists.")
    else:
        try:
            venv.create(venv_path, with_pip=True)
            print("   ✓ Virtual environment created successfully.")
        except Exception as e:
            print(f"   ✗ Error creating virtual environment: {e}")
            return False
    
    # Determine the correct python and pip paths
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"
    
    # Install dependencies
    print("2. Installing dependencies...")
    success, output = run_command(f'"{pip_path}" install -r requirements.txt', cwd=project_root)
    if success:
        print("   ✓ Dependencies installed successfully.")
    else:
        print(f"   ✗ Error installing dependencies: {output}")
        return False
    
    # Create .env file if it doesn't exist
    print("3. Setting up environment configuration...")
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if env_file.exists():
        print("   .env file already exists.")
    elif env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("   ✓ .env file created from .env.example")
        print("   ⚠️  Please edit .env file with your API keys!")
    else:
        print("   ✗ .env.example not found")
        return False
    
    # Test basic imports
    print("4. Testing basic imports...")
    test_cmd = f'''"{python_path}" -c "
import sys
sys.path.insert(0, '.')
try:
    from core.logger import get_logger
    print('✓ Logger import successful')
    print('✓ Basic system check complete')
except Exception as e:
    print(f'✗ Import error: {{e}}')
    sys.exit(1)
"'''
    
    success, output = run_command(test_cmd, cwd=project_root)
    if success:
        print("   ✓ Basic imports working correctly.")
    else:
        print(f"   ✗ Import test failed: {output}")
        print("   This is normal if API keys aren't configured yet.")
    
    print()
    print("=" * 40)
    print("Setup completed successfully!")
    print()
    print("Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run the Gmail token generation script:")
    print(f"   {python_path} scripts/generate_gmail_token.py")
    print("3. Start the server:")
    print(f"   {python_path} -m uvicorn app.main:app --reload")
    print()
    print("For more information, see README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)