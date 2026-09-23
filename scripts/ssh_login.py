#!/usr/bin/env python3
"""Job 03 - Se connecte en SSH a un serveur et lance une commande shell."""

import sys
import paramiko

# Import de la config centrale (dossier parent)
sys.path.append("/home/monitor/psmm")
import config


def ssh_run(nom_serveur, commande):
    """Connexion SSH par cle a un serveur et execution d'une commande."""
    srv = config.SERVEURS[nom_serveur]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        hostname=srv["host"],
        username=srv["user"],
        key_filename=config.SSH_KEY,
    )

    stdin, stdout, stderr = client.exec_command(commande)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()

    return sortie, erreur


if __name__ == "__main__":
    serveur = "ftp"        # serveur cible
    commande = "df -h"     # commande shell a lancer

    print(f"[+] Connexion a {serveur} ({config.SERVEURS[serveur]['host']})")
    print(f"[+] Commande : {commande}\n")

    sortie, erreur = ssh_run(serveur, commande)

    if sortie:
        print(sortie)
    if erreur:
        print("[!] Erreur :", erreur)

