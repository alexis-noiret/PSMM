#!/usr/bin/env python3
"""Job 09 - Envoie a l'admin un mail recap des tentatives d'acces de la veille.
Requete les 3 tables (sql/ftp/web), met en forme, envoie via SMTP."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config
from mailer import envoyer_mail

# Nombre de jours en arriere : 1 = hier (la veille, comme demande).
# Mettre 0 pour tester avec les tentatives d'aujourd'hui.
JOURS_ARRIERE = 0

SRV = config.SERVEURS["mariadb"]
TABLES = {
    "SQL (MariaDB)": "sql_errors",
    "FTP": "ftp_errors",
    "Web (Apache)": "web_errors",
}


def ssh_query(requete):
    """Execute une requete SQL sur mariadb via SSH et renvoie la sortie brute."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=SRV["host"], username=SRV["user"],
                   key_filename=config.SSH_KEY)
    cmd = f'sudo mariadb -N -e "{requete}"'
    stdin, stdout, stderr = client.exec_command(cmd)
    sortie = stdout.read().decode()
    client.close()
    return sortie


def recuperer_tentatives(table):
    """Recupere les tentatives d'un jour donne (J - JOURS_ARRIERE)."""
    requete = (
        f"SELECT compte, date_heure, ip FROM psmm.{table} "
        f"WHERE DATE(date_heure) = DATE(NOW() - INTERVAL {JOURS_ARRIERE} DAY) "
        f"ORDER BY date_heure;"
    )
    sortie = ssh_query(requete)
    lignes = []
    for ligne in sortie.splitlines():
        if ligne.strip():
            # mariadb -N separe les colonnes par des tabulations
            champs = ligne.split("\t")
            if len(champs) == 3:
                lignes.append(champs)
    return lignes


def construire_corps():
    """Construit le corps du mail avec les 3 sources, en tableau aligne."""
    jour = "aujourd'hui" if JOURS_ARRIERE == 0 else f"J-{JOURS_ARRIERE} (la veille)"
    corps = [f"Rapport des tentatives d'acces echouees - {jour}", "=" * 55, ""]

    total = 0
    for titre, table in TABLES.items():
        tentatives = recuperer_tentatives(table)
        total += len(tentatives)
        corps.append(f"### {titre} : {len(tentatives)} tentative(s)")
        if tentatives:
            corps.append(f"{'Compte':<20}{'Date/heure':<22}{'IP':<16}")
            corps.append("-" * 55)
            for compte, date_heure, ip in tentatives:
                corps.append(f"{compte:<20}{date_heure:<22}{ip:<16}")
        else:
            corps.append("(aucune)")
        corps.append("")

    corps.append("=" * 55)
    corps.append(f"TOTAL : {total} tentative(s) sur l'ensemble des services.")
    return "\n".join(corps)


if __name__ == "__main__":
    print("[*] Construction du rapport...")
    corps = construire_corps()
    print(corps)
    print("\n[*] Envoi du mail...")
    envoyer_mail("[PSMM] Rapport tentatives d'acces", corps)
    print("[+] Mail envoye a l'administrateur")
