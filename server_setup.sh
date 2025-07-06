#!/bin/bash
# Email Agent Server Setup Script
# Führt alle Installationen und Konfigurationen automatisch durch

set -e  # Bei Fehler stoppen

echo "🚀 Starting Email Agent Server Setup..."

# System Update
echo "📦 Updating system packages..."
sudo apt update -y
sudo apt install -y git python3 python3-venv python3-pip

# Verzeichnis erstellen und Repo klonen
echo "📂 Setting up directories and cloning repository..."
mkdir -p ~/apps
cd ~/apps

# Existierendes Verzeichnis löschen falls vorhanden
if [ -d "email_agent_v1" ]; then
    echo "⚠️  Removing existing email_agent_v1 directory..."
    rm -rf email_agent_v1
fi

# Repository klonen
git clone https://github.com/Vortex-Labs-xyz/email_agent_v1.git
cd email_agent_v1

# Python Virtual Environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# .env Datei erstellen
echo "📝 Creating .env template..."
cat > .env <<'ENV'
# ========================================
# Email Agent Configuration
# Bitte füllen Sie alle Werte aus!
# ========================================

# ---------- Gmail API ----------
# Von Google Cloud Console
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
DELEGATED_USER=matthias@vortexgroup.xyz

# ---------- AWS ----------
# Von AWS IAM Console
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-central-1
S3_BUCKET=invoice-archive-123456789012

# ---------- PostgreSQL ----------
# Von Ihrer Datenbank
PGHOST=
PGPORT=5432
PGUSER=
PGPASSWORD=
PGDATABASE=email_analytics

# ---------- Todoist (Optional) ----------
TODOIST_TOKEN=
ENV

chmod 600 .env

# Systemd Service erstellen
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/email-agent.service >/dev/null <<'SERVICE'
[Unit]
Description=Vortex Email Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/apps/email_agent_v1
EnvironmentFile=/home/ubuntu/apps/email_agent_v1/.env
ExecStart=/home/ubuntu/apps/email_agent_v1/.venv/bin/python main.py
Restart=on-failure
RestartSec=30
User=ubuntu
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Systemd Timer erstellen
echo "⏰ Creating systemd timer..."
sudo tee /etc/systemd/system/email-agent.timer >/dev/null <<'TIMER'
[Unit]
Description=Run Email Agent every 5 minutes
Requires=email-agent.service

[Timer]
OnBootSec=30
OnUnitActiveSec=5min
Unit=email-agent.service

[Install]
WantedBy=timers.target
TIMER

# Services neu laden
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Timer aktivieren (aber noch nicht starten)
echo "✅ Enabling timer (not starting yet)..."
sudo systemctl enable email-agent.timer

echo "
════════════════════════════════════════════════════════
✅ SETUP ERFOLGREICH ABGESCHLOSSEN!
════════════════════════════════════════════════════════

📋 NÄCHSTE SCHRITTE:

1. Öffnen Sie die .env Datei und tragen Sie Ihre Secrets ein:
   nano ~/apps/email_agent_v1/.env

2. Testen Sie die Konfiguration:
   cd ~/apps/email_agent_v1
   source .venv/bin/activate
   python main.py
   deactivate

3. Wenn alles funktioniert, starten Sie den Timer:
   sudo systemctl start email-agent.timer

4. Überprüfen Sie den Status:
   sudo systemctl status email-agent.timer
   sudo journalctl -u email-agent.service -f

════════════════════════════════════════════════════════
"

# Pfad zur .env Datei anzeigen
echo "📍 .env Datei befindet sich hier:"
echo "   ~/apps/email_agent_v1/.env"
echo ""
echo "Verwenden Sie 'nano ~/apps/email_agent_v1/.env' zum Bearbeiten" 