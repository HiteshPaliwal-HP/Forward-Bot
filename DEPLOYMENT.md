# Forward Bot — Deployment Guide

A complete reference for deploying, updating, and maintaining the Forward Bot on the Oracle Cloud VM.

---

## 📦 Stack Overview

| Component | Technology |
|---|---|
| **Server** | Oracle Cloud Free Tier VM — Ubuntu 22.04 LTS |
| **Region** | `ap-mumbai-1` |
| **Runtime** | Python 3.12 via `uv` |
| **Web Framework** | FastAPI + Uvicorn |
| **Frontend** | Vite (React + TypeScript) |
| **Database** | MongoDB Atlas (cloud-hosted) |
| **Telegram Client** | Telethon |
| **Process Manager** | systemd |

---

## 🖥️ Server Details

| Detail | Value |
|---|---|
| **Public IP** | `130.210.17.247` |
| **Internal IP** | `10.0.0.138` |
| **OS User** | `ubuntu` |
| **Hostname** | `forwardbot` |
| **SSH Key** | `OracleKeys/ssh-key-2026-08-09.key` |

---

## 🔑 SSH Access

### Connect to the Server

```powershell
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -i "C:\Users\Hitesh - HP\OneDrive\Documents\Github\Forward-Bot\OracleKeys\ssh-key-2026-08-09.key" ubuntu@130.210.17.247
```

---

## 📁 Directory Layout on Server

```
/home/ubuntu/
├── Forward-Bot/                  ← Git repo (cloned from GitHub)
│   ├── forward-bot/              ← Python backend (FastAPI)
│   │   ├── src/forward_bot/      ← Application source
│   │   ├── .venv/                ← Python virtualenv (created by uv)
│   │   └── .env                  ← Environment variables (NOT in git)
│   ├── web/                      ← Frontend source (React/Vite)
│   └── auth_telegram.py          ← One-time Telegram auth script
│
/app/
├── data/
│   ├── telegram.session          ← Telegram session file (keep safe!)
│   └── replacement-images/       ← Media replacement directory
└── static/                       ← Built web UI (served by FastAPI)
    ├── index.html
    └── assets/
```

---

## ⚙️ Environment Variables

The `.env` file lives at `~/Forward-Bot/forward-bot/.env` on the server.
It is **NOT tracked by git** — never commit secrets.

```env
MONGO_URI=mongodb+srv://<user>:<pass>@cluster0forwardbot.e7b5lsl.mongodb.net/ForwardBot?retryWrites=true&w=majority
API_KEY=tbcopyforwaderapp
SECRET_KEY=tradingbulls
TELEGRAM_SESSION_PATH=/app/data/telegram.session
MEDIA_REPLACEMENT_BASE_DIR=/app/data/replacement-images
TIMEZONE_DEFAULT=UTC
SAMPLING_PERSIST=false
UI_ENABLED=true
LOG_RING_BUFFER_HOURS=1
HOT_RELOAD_INTERVAL=30
DELIVERY_MAX_RETRIES=3
DELIVERY_BACKOFF_FACTOR=2.0
DELIVERY_BASE_DELAY=1.0
BIND_HOST=0.0.0.0
TELEGRAM_API_ID=37216686
TELEGRAM_API_HASH=82f6a42a5f26422d56b5a7afafe1d7f9
```

> If you recreate the server you must recreate this file manually.

---

## 🔧 Managing Environment Variables on the Server

All env changes require a bot restart to take effect.

### Open the .env file for editing

```bash
nano ~/Forward-Bot/forward-bot/.env
```

Use arrow keys to navigate, make changes, then save with **Ctrl+X → Y → Enter**.

---

### ➕ Add a New Variable

Open the file and add a new line at the bottom:

```bash
nano ~/Forward-Bot/forward-bot/.env
```

Add at the bottom:
```
NEW_VARIABLE=value
```

Save and restart:
```bash
sudo systemctl restart forward-bot
```

---

### ✏️ Update an Existing Variable

```bash
nano ~/Forward-Bot/forward-bot/.env
```

Find the line (e.g. `API_KEY=oldvalue`), change the value, save and restart:
```bash
sudo systemctl restart forward-bot
```

Or use `sed` for quick one-liner updates (no editor needed):
```bash
# Replace the value of an existing key
sed -i 's/^API_KEY=.*/API_KEY=newvalue/' ~/Forward-Bot/forward-bot/.env

# Verify the change
grep API_KEY ~/Forward-Bot/forward-bot/.env

# Restart
sudo systemctl restart forward-bot
```

---

### ❌ Delete a Variable

```bash
nano ~/Forward-Bot/forward-bot/.env
```

Delete the line for that variable, save and restart:
```bash
sudo systemctl restart forward-bot
```

Or use `sed` to delete by key name:
```bash
sed -i '/^VARIABLE_NAME=/d' ~/Forward-Bot/forward-bot/.env
sudo systemctl restart forward-bot
```

---

### 📋 View All Current Variables

```bash
cat ~/Forward-Bot/forward-bot/.env
```

Or view without comments/blank lines:
```bash
grep -v '^#' ~/Forward-Bot/forward-bot/.env | grep -v '^$'
```

---

### ✅ Verify a Variable is Loaded

After restarting, check the logs to confirm the bot started correctly:
```bash
sudo journalctl -u forward-bot -n 20 --no-pager
```

---

## 🚀 Deploying a Code Change (Standard Workflow)

### Step 1 — Make changes locally and push to GitHub

```bash
git add .
git commit -m "your change description"
git push origin main
```

### Step 2 — SSH into the server

```powershell
ssh -i "C:\Users\Hitesh - HP\OneDrive\Documents\Github\Forward-Bot\OracleKeys\ssh-key-2026-08-09.key" ubuntu@130.210.17.247
```

### Step 3 — Pull latest code

```bash
cd ~/Forward-Bot
git pull
```

### Step 4 — Restart the backend service

```bash
sudo systemctl restart forward-bot
```

### Step 5 — Verify it started correctly

```bash
sudo journalctl -u forward-bot -n 30 --no-pager
```

Look for these lines to confirm success:
```
Connected to MongoDB successfully
Telegram client connected and authorized successfully
Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

---

## 🌐 Deploying Frontend (Web UI) Changes

The web UI is built locally and uploaded to the server.

### Step 1 — Build locally (Windows PowerShell)

```powershell
cd "C:\Users\Hitesh - HP\OneDrive\Documents\Github\Forward-Bot\web"
npx vite build
```

> Use `npx vite build` (not `npm run build`) to skip TypeScript test errors.

### Step 2 — Upload built files to server

```powershell
scp -r -i "C:\Users\Hitesh - HP\OneDrive\Documents\Github\Forward-Bot\OracleKeys\ssh-key-2026-08-09.key" "C:\Users\Hitesh - HP\OneDrive\Documents\Github\Forward-Bot\web\dist" ubuntu@130.210.17.247:/tmp/web-dist
```

### Step 3 — Deploy on server (SSH window)

```bash
sudo cp -r /tmp/web-dist/* /app/static/
sudo chown -R ubuntu:ubuntu /app/static/
sudo systemctl restart forward-bot
```

### Step 4 — Hard refresh browser

Open `http://130.210.17.247:8000` and press `Ctrl+Shift+R`.

---

## 🛠️ Service Management Commands

```bash
# Check status
sudo systemctl status forward-bot

# Start
sudo systemctl start forward-bot

# Stop
sudo systemctl stop forward-bot

# Restart (use after any backend code change)
sudo systemctl restart forward-bot

# View live logs
sudo journalctl -u forward-bot -f

# View last 50 lines
sudo journalctl -u forward-bot -n 50 --no-pager
```

---

## 📱 Telegram Session Setup (First Time or After Session Expiry)

### Step 1 — Stop the bot

```bash
sudo systemctl stop forward-bot
```

### Step 2 — Run the auth script

```bash
cd ~/Forward-Bot/forward-bot
uv run python ~/Forward-Bot/auth_telegram.py
```

Enter your **phone number** (e.g. `+91xxxxxxxxxx`) then the **OTP** from your Telegram app.

Session saved to: `/app/data/telegram.session`

### Step 3 — Restart the bot

```bash
sudo systemctl start forward-bot
```

> ⚠️ Keep the session file safe — if deleted, you must re-authenticate.
> The session file is NOT in git.

---

## 🔐 Oracle Cloud Firewall (Ingress Rules Required)

| Port | Protocol | Purpose |
|---|---|---|
| 22 | TCP | SSH access |
| 80 | TCP | HTTP |
| 443 | TCP | HTTPS |
| 8000 | TCP | Forward Bot Web UI |

Location: Oracle Console → VCN → Security Lists → Add Ingress Rule

---

## 🍃 MongoDB Atlas — Whitelist Server IP

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. **Security → Network Access → Add IP Address**
3. Add `130.210.17.247`

---

## 🌍 Accessing the Web UI

```
http://130.210.17.247:8000
```

**Login:** Enter API Key → `tbcopyforwaderapp`

---

## 🧰 Troubleshooting

| Problem | Fix |
|---|---|
| MongoDB connection failed | Whitelist server IP in MongoDB Atlas |
| Telegram session error | Re-run `auth_telegram.py` |
| Web UI shows `Not Found` | Re-deploy frontend to `/app/static/` |
| Can't SSH | Check Oracle Security List has port 22 open |
| Bot crashes in loop | Check `journalctl` logs for error message |

---

## 📋 Full Fresh Server Setup (From Scratch)

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install git and curl
sudo apt install -y git curl

# 3. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 4. Clone repo
git clone https://github.com/HiteshPaliwal-HP/Forward-Bot.git ~/Forward-Bot

# 5. Create data and static directories
sudo mkdir -p /app/data/replacement-images /app/static
sudo chown -R ubuntu:ubuntu /app

# 6. Create .env file
nano ~/Forward-Bot/forward-bot/.env
# Paste env variables (see Environment Variables section above)

# 7. Install Python dependencies
cd ~/Forward-Bot/forward-bot
uv sync

# 8. Create systemd service
sudo nano /etc/systemd/system/forward-bot.service
# Paste the service file content below

sudo systemctl daemon-reload
sudo systemctl enable forward-bot

# 9. Authenticate Telegram (interactive — one time)
uv run python ~/Forward-Bot/auth_telegram.py

# 10. Start the bot
sudo systemctl start forward-bot

# 11. Deploy web UI (from local Windows PowerShell)
# npx vite build  (run in web/ folder)
# scp dist/ to server, copy to /app/static/
```

### systemd Service File

Path: `/etc/systemd/system/forward-bot.service`

```ini
[Unit]
Description=Forward Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Forward-Bot/forward-bot
ExecStart=/home/ubuntu/.local/bin/uv run python -m forward_bot
Restart=always
RestartSec=10
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

---

*Last updated: September 2026*
