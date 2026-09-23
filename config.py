# config.py — configuration centrale du projet PSMM

import os
from dotenv import load_dotenv

load_dotenv("/home/monitor/psmm/.env")

# --- Serveurs (reseau plateforme / bridge ethernet) ---
SERVEURS = {
    "ftp":     {"host": "10.10.12.149", "user": "monitor"},
    "web":     {"host": "10.10.12.146", "user": "monitor"},
    "mariadb": {"host": "10.10.12.148", "user": "monitor"},
}

SSH_KEY = "/home/monitor/.ssh/id_ed25519"

# --- Mail (Gmail/Workspace SMTP) ---
MAIL = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "expediteur": os.environ.get("MAIL_EXPEDITEUR"),
    "app_password": os.environ.get("MAIL_APP_PASSWORD"),
    "destinataire": os.environ.get("MAIL_DESTINATAIRE"),
}
# --- Google Chat (webhook) ---
CHAT_WEBHOOK = os.environ.get("CHAT_WEBHOOK")
