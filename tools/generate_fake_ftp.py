#!/usr/bin/env python3
"""Utilitaire de TEST - genere de fausses tentatives d'acces FTP.
Alimente les logs vsftpd pour tester le collecteur. Pas un livrable."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config

SRV = config.SERVEURS["ftp"]
FAUX_COMPTES = ["pirate", "root", "webadmin", "guest"]


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
        # tentative FTP echouee via le client ftp local sur le serveur
        cmd = f"ftp -inv 127.0.0.1 <<'EOF'\nuser {user} mauvaismdp\nbye\nEOF"
        ssh_exec(cmd)
    print(f"[+] {len(FAUX_COMPTES)} fausses tentatives FTP generees")
