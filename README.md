# geo-proxy-relay

A lightweight FastAPI reverse proxy designed to bypass geo-IP restrictions.
Runs on a Raspberry Pi and relays HTTP requests from websites/services hosted in other countries
to local websites that block international traffic.

---

## How it works

```
Odoo (foreign-hosted)  ──→  https://proxy.yourdomain.com/exchange-rate
                              │
                    [Cloudflare Tunnel]
                              │
                Raspberry Pi @ localhost:8080
                      (inside Cambodia)
                              │
                    Target Cambodia site
```

The blocked website/service sends a request with an `X-Target-URL` header. The proxy forwards it to that URL from inside Cambodia and returns the response.

---

## Requirements

- Raspberry Pi 3B running a Ubuntu Server
- Python 3.10+
- Cloudflare account with a domain
- `cloudflared` installed on the Pi

---

## Project structure

```
/opt/geo-proxy-relay/
├── main.py
├── requirements.txt
├── .env
└── .venv/
```

---

## Installation

### 1. Create project directory

```bash
sudo mkdir -p /opt/geo-proxy-relay
cd /opt/geo-proxy-relay
```

### 2. Virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment variables

```bash
nano .env
```

```env
API_KEY=your-secret-key-here
```

---

## Running locally (dev)

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Health check

```bash
curl http://localhost:8080/health
```

### Forward request

```bash
curl -X GET http://localhost:8080/exchange-rate \
  -H "X-API-Key: your-secret-key-here" \
  -H "X-Target-URL: https://target-cambodia-site.com/exchange_rate.php"
```

---

## Cloudflare Tunnel setup

### Install cloudflared

```bash
# Add Cloudflare's GPG key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-public-v2.gpg | sudo tee /usr/share/keyrings/cloudflare-public-v2.gpg >/dev/null

# Add the repository to apt
echo "deb [signed-by=/usr/share/keyrings/cloudflare-public-v2.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt update
sudo apt install cloudflared
```

### Create tunnel via Cloudflare dashboard

1. Go to **Cloudflare Zero Trust** → **Networks** → **Tunnels**
2. Click **Create a tunnel** → give it a proper name (for example, `proxy-relay-tunnel`)
3. Under **Public Hostname**, add:

| Field        | Value            |
| ------------ | ---------------- |
| Subdomain    | `proxy`          |
| Domain       | `yourdomain.com` |
| Service Type | `HTTP`           |
| URL          | `localhost:8080` |

---

## Systemd service

```bash
sudo ln -s /opt/geo-proxy-relay/geo-proxy-relay.service /etc/systemd/system/
```

```ini
[Unit]
Description=Geo Proxy Relay (FastAPI)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/geo-proxy-relay
EnvironmentFile=/opt/geo-proxy-relay/.env
ExecStart=/opt/geo-proxy-relay/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable both services

```bash
sudo systemctl daemon-reload

sudo systemctl enable geo-proxy-relay
sudo systemctl start geo-proxy-relay

sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

---

## Useful commands

```bash
# Check service status
sudo systemctl status geo-proxy-relay
sudo systemctl status cloudflared

# Live logs
sudo journalctl -u geo-proxy-relay -f
sudo journalctl -u cloudflared -f

# Restart after code change
sudo systemctl restart geo-proxy-relay

# Check Raspberry Pi temperature
watch -n 2 vcgencmd measure_temp
```

---

## Calling from Odoo

Store the API key in Odoo system parameters under **Settings → Technical → System Parameters**:

```
Key:   proxy_relay.api_key
Value: your-secret-key-here
```

Then in your Odoo module:

```python
import requests

api_key = self.env['ir.config_parameter'].sudo().get_param('proxy_relay.api_key')

response = requests.get(
    "https://proxy.yourdomain.com/exchange-rate",
    headers={
        "X-API-Key": api_key,
        "X-Target-URL": "https://target-cambodia-site.com/exchange_rate.php",
    },
    timeout=30,
)
response.raise_for_status()
data = response.json()
```

---

## Security notes

- API key is passed via `X-API-Key` header — safe over HTTPS
- Cloudflare handles TLS — no SSL cert management needed on the Pi
- Systemd service runs as `root` user

---

## Hardware

| Component | Spec                        |
| --------- | --------------------------- |
| Board     | Raspberry Pi 3B             |
| CPU       | 4× ARM Cortex-A53 @ 1.2GHz  |
| RAM       | 1 GB LPDDR2                 |
| Network   | 100 Mbps (over USB 2.0 bus) |
| Storage   | microSD                     |
