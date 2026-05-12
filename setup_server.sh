#!/bin/bash

# HLQuant Server Setup Script
# Run this once on the server to initialize the environment.

echo "🛠️ Starting HLQuant Server Setup..."

# 1. 필수 패키지 설치
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git

# 2. 디렉토리 이동 및 가상환경 생성
cd ~/HLQuant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 서비스 파일 등록
echo "⚙️ Registering systemd service..."
sudo cp docs/hlquant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hlquant.service
sudo systemctl start hlquant.service

echo "✅ Setup Complete! Bot is now running as a service."
sudo systemctl status hlquant.service --no-pager
