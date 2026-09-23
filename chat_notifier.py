#!/usr/bin/env python3
"""Module partage - envoi de messages dans Google Chat via webhook."""

import sys
import requests

sys.path.append("/home/monitor/psmm")
import config


def envoyer_chat(message):
    """Envoie un message texte dans le Space Google Chat."""
    r = requests.post(config.CHAT_WEBHOOK, json={"text": message}, timeout=10)
    return r.status_code == 200
