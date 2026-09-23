#!/usr/bin/env python3
"""Utilitaire de TEST - genere de fausses tentatives d'acces MariaDB.
Sert uniquement a alimenter les logs pour tester/demontrer le collecteur.
N'est PAS un livrable de supervision."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config

SRV = config.SERVEURS["mariadb"]
FAUX_COMPTES = ["hacker", "admin", "root_fake", "test123"]


def ssh_exec(commande):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=SRV["host"], username=SRV["user"],
                   key_filename=config.SSH_KEY)
    client.exec_command(commande)
    client.close()


if __name__ == "__main__":
    for user in FAUX_COMPTES:
        ssh_exec(f"mariadb -u {user} -pmauvaismdp 2>/dev/null")
    print(f"[+] {len(FAUX_COMPTES)} fausses tentatives generees sur MariaDB")
