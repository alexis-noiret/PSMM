#!/usr/bin/env python3
"""Utilitaire de TEST - genere de fausses tentatives d'acces web (auth basic).
Alimente les logs Apache pour tester le collecteur. Pas un livrable."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config

SRV = config.SERVEURS["web"]
FAUX_COMPTES = ["pirate", "admin", "root", "intrus"]


def ssh_exec(commande):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=SRV["host"], username=SRV["user"],
                   key_filename=config.SSH_KEY)
    stdin, stdout, stderr = client.exec_command(commande)
    stdout.read()
    client.close()


if __name__ == "__main__":
    for user in FAUX_COMPTES:
        ssh_exec(f"curl -s -u {user}:mauvaismdp http://127.0.0.1/ -o /dev/null")
    print(f"[+] {len(FAUX_COMPTES)} fausses tentatives web generees")
