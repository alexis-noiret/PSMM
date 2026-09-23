#!/usr/bin/env python3
"""Job 04 - Se connecte en SSH et lance une commande en sudo (NOPASSWD)."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config


def ssh_run_sudo(nom_serveur, commande):
    """Execute une commande prefixee de sudo sur un serveur distant."""
    srv = config.SERVEURS[nom_serveur]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=srv["host"],
        username=srv["user"],
        key_filename=config.SSH_KEY,
    )

    stdin, stdout, stderr = client.exec_command(f"sudo {commande}")
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()

    return sortie, erreur


if __name__ == "__main__":
    serveur = "ftp"
    commande = "tail -n 3 /etc/hostname"

    print(f"[+] Connexion a {serveur} ({config.SERVEURS[serveur]['host']})")
    print(f"[+] Commande sudo : {commande}\n")

    sortie, erreur = ssh_run_sudo(serveur, commande)

    if sortie:
        print("Sortie :\n" + sortie)
    if erreur:
        print("[!] stderr :", erreur)
