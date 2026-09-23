#!/usr/bin/env python3
"""Job 10 - Sauvegarde horodatee de la base psmm sur le serveur mariadb.
Conserve les 7 dernieres sauvegardes. Prevu pour tourner en cron (toutes les 3h)."""

import sys
from datetime import datetime
import paramiko

sys.path.append("/home/monitor/psmm")
import config

SRV = config.SERVEURS["mariadb"]
DOSSIER_BACKUP = "/home/monitor/backups"
NB_A_CONSERVER = 7


def ssh_exec(commande):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=SRV["host"], username=SRV["user"],
                   key_filename=config.SSH_KEY)
    stdin, stdout, stderr = client.exec_command(commande)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()
    return sortie, erreur


def sauvegarder():
    """Cree un dump horodate de la base psmm sur le serveur mariadb."""
    horodatage = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fichier = f"{DOSSIER_BACKUP}/psmm_{horodatage}.sql"

    # cree le dossier si besoin, puis dump la base dedans
    cmd = (
        f"mkdir -p {DOSSIER_BACKUP} && "
        f"sudo mariadb-dump psmm > {fichier} && "
        f"echo OK"
    )
    sortie, erreur = ssh_exec(cmd)
    if "OK" in sortie:
        print(f"[+] Sauvegarde creee : {fichier}")
        return True
    print(f"[!] Echec de la sauvegarde : {erreur}")
    return False


def nettoyer_anciennes():
    """Ne conserve que les NB_A_CONSERVER sauvegardes les plus recentes."""
    # liste les .sql tries du plus recent au plus ancien, saute les 7 premiers,
    # supprime le reste
    cmd = (
        f"ls -1t {DOSSIER_BACKUP}/psmm_*.sql 2>/dev/null | "
        f"tail -n +{NB_A_CONSERVER + 1} | "
        f"xargs -r rm -v"
    )
    sortie, _ = ssh_exec(cmd)
    if sortie.strip():
        print(f"[+] Anciennes sauvegardes supprimees :\n{sortie}")
    else:
        print(f"[*] Rien a supprimer (<= {NB_A_CONSERVER} sauvegardes)")


def lister():
    """Affiche les sauvegardes presentes."""
    sortie, _ = ssh_exec(f"ls -1t {DOSSIER_BACKUP}/psmm_*.sql 2>/dev/null")
    nb = len(sortie.splitlines())
    print(f"[*] {nb} sauvegarde(s) presente(s) :")
    print(sortie)


if __name__ == "__main__":
    if sauvegarder():
        nettoyer_anciennes()
        lister()
