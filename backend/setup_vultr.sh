#!/bin/bash

# ElasticSeer Vultr Automated Setup Script
# This script automates the backend deployment on Ubuntu 22.04+

set -e

echo "🚀 Starting ElasticSeer Backend Setup..."

# 1. Install System Dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv git

# 2. Setup Virtual Environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Install Python Dependencies
echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo "Please create a .env file in this directory with your credentials."
    echo "You can do this now in another terminal or later before starting the service."
fi

# 5. Create Systemd Service File
echo "⚙️  Configuring systemd service..."
PROJECT_ROOT=$(pwd)
SERVICE_FILE="[Unit]
Description=ElasticSeer FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_ROOT
Environment=\"PATH=$PROJECT_ROOT/venv/bin\"
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$PROJECT_ROOT/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001

[Install]
WantedBy=multi-user.target"

echo "$SERVICE_FILE" | sudo tee /etc/systemd/system/elasticseer.service > /dev/null

# 6. Final Instructions
echo "✅ Setup complete!"
echo "--------------------------------------------------------"
echo "Next steps:"
echo "1. Ensure your .env file is populated with correct secrets."
echo "2. Start the service: sudo systemctl start elasticseer"
echo "3. Enable on boot:   sudo systemctl enable elasticseer"
echo "4. Check status:     sudo systemctl status elasticseer"
echo "5. IMPORTANT: Open port 8001 in your Vultr Firewall!"
echo "--------------------------------------------------------"
