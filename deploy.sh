#!/usr/bin/env bash
# Deploy script for Email Agent v1
# This script is called by GitHub Actions after each push

set -e  # Exit on error

echo "🚀 Starting deployment to cursor-srv..."

# Deploy to server
ssh cursor-srv <<'REMOTE_COMMANDS'
set -e

echo "📦 Pulling latest changes..."
cd ~/apps/email_agent_v1
git pull --ff-only

echo "🐍 Updating Python dependencies..."
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate

echo "🔄 Restarting email-agent service..."
sudo systemctl restart email-agent.service

echo "✅ Service restarted successfully"

# Show service status
echo "📊 Current service status:"
sudo systemctl is-active email-agent.service || true
sudo systemctl is-active email-agent.timer || true

# Show last few log lines
echo "📋 Recent logs:"
sudo journalctl -u email-agent.service -n 10 --no-pager

REMOTE_COMMANDS

echo "✅ Deploy completed successfully!" 