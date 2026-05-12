#!/bin/bash

# HLQuant Deployment Script
# Usage: ./deploy.sh

PROJECT_DIR="/home/yinamsu/HLQuant"

echo "🚀 Starting HLQuant Deployment..."

# 1. 이동
cd $PROJECT_DIR || { echo "❌ Directory not found"; exit 1; }

# 2. 최신 코드 가져오기
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# 3. 가상환경 활성화 및 패키지 설치
echo "📦 Updating dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 4. 서비스 재시작
echo "🔄 Restarting HLQuant service..."
sudo systemctl restart hlquant.service

echo "✅ HLQuant Deployment Completed!"
sudo systemctl status hlquant.service --no-pager
