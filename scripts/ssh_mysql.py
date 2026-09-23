#!/usr/bin/env python3
"""Job 05 - Verifie l'acces au serveur MariaDB via SSH."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config


def mysql_query(requete):
    """Execute une requete SQL sur le serveur mariadb via SSH + sudo mariadb."""
    srv = config.SERVEURS["mariadb"]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=srv["host"],
        username=srv["user"],
        key_filename=config.SSH_KEY,
    )

    # -e execute la requete, guillemets echappes pour le shell distant
    commande = f'sudo mariadb -e "{requete}"'
    stdin, stdout, stderr = client.exec_command(commande)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()

    return sortie, erreur


if __name__ == "__main__":
    requete = "SHOW DATABASES;"

    print(f"[+] Serveur MariaDB : {config.SERVEURS['mariadb']['host']}")
    print(f"[+] Requete : {requete}\n")

    sortie, erreur = mysql_query(requete)

    if sortie:
        print("Bases de donnees :\n" + sortie)
    if erreur:
        print("[!] stderr :", erreur)
