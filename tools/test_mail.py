#!/usr/bin/env python3
"""Test minimal - verifie que l'envoi de mail via Gmail/Workspace fonctionne."""

import sys
import smtplib
from email.mime.text import MIMEText

sys.path.append("/home/monitor/psmm")
import config

M = config.MAIL

msg = MIMEText("Test d'envoi depuis le projet PSMM. Si tu lis ceci, ca marche.")
msg["Subject"] = "[PSMM] Test mail"
msg["From"] = M["expediteur"]
msg["To"] = M["destinataire"]

try:
    serveur = smtplib.SMTP(M["smtp_server"], M["smtp_port"])
    serveur.starttls()
    serveur.login(M["expediteur"], M["app_password"])
    serveur.send_message(msg)
    serveur.quit()
    print("[+] Mail envoye avec succes")
except Exception as e:
    print("[!] Erreur :", e)
