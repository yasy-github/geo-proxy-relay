#!/bin/bash
set -e
echo "==> Cleaning up previous Docker repo config"
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -f /etc/apt/keyrings/docker.gpg

echo "==> Updating system"
sudo apt update && sudo apt upgrade -y

echo "==> Removing conflicting packages"
sudo apt remove -y containerd docker docker.io docker-compose
sudo apt autoremove -y

echo "==> Installing Docker from official repo"
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y git python3 python3-pip python3-venv \
  docker-ce docker-ce-cli containerd.io docker-compose-plugin

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
