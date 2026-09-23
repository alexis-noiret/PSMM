#!/usr/bin/env python3
"""Module partage - envoi de mail via Gmail/Workspace SMTP.
Reutilise par tous les scripts qui notifient l'admin."""

import sys
import smtplib
from email.mime.text import MIMEText

sys.path.append("/home/monitor/psmm")
import config


def envoyer_mail(sujet, corps):
    """Envoie un mail texte a l'administrateur."""
    M = config.MAIL
    msg = MIMEText(corps)
    msg["Subject"] = sujet
    msg["From"] = M["expediteur"]
    msg["To"] = M["destinataire"]

    serveur = smtplib.SMTP(M["smtp_server"], M["smtp_port"])
    serveur.starttls()
    serveur.login(M["expediteur"], M["app_password"])
    serveur.send_message(msg)
    serveur.quit()
