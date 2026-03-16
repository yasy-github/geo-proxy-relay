#!/bin/bash
set -e

echo "==> Updating system"
sudo apt update && sudo apt upgrade -y

echo "==> Installing dependencies"
sudo apt install -y python3 python3-pip python3-venv git docker.io docker-compose

echo "==> Enabling Docker"
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "==> Installing cloudflared"
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
chmod +x cloudflared-linux-arm
sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared

echo "==> Cloning project"
sudo mkdir -p /opt/geo-proxy-relay
sudo chown $USER:$USER /opt/geo-proxy-relay
git clone https://github.com/yasy-github/geo-proxy-relay.git /opt/geo-proxy-relay
cd /opt/geo-proxy-relay

echo "==> Setting up .env"
cp .env.example .env
echo "!! Edit /opt/geo-proxy-relay/.env with your API key before continuing"
read -p "Press enter when ready..."

echo "==> Starting app"
docker compose up -d

echo "==> Installing geo-proxy-relay systemd service"
sudo ln -s /opt/geo-proxy-relay/geo-proxy-relay.service /etc/systemd/system/geo-proxy-relay.service

sudo systemctl daemon-reload
sudo systemctl enable geo-proxy-relay
sudo systemctl start geo-proxy-relay

echo "==> Done. Proxy is running at http://localhost:8080"