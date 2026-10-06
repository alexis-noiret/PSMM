#!/usr/bin/env python3
"""Job 20 - Rapport mail des tentatives d'acces collectees par rsyslog.
Lit la table acces_errors (compte MariaDB lecture seule) via SSH.
N'envoie que les NOUVELLES tentatives depuis le dernier mail (suivi du
dernier id, pas de doublon). Mise en forme en 3 sections (SQL/FTP/Web).
Prevu pour tourner chaque matin en cron."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config
from mailer import envoyer_mail

MARIADB = config.SERVEURS["mariadb"]
FICHIER_ETAT = "/home/monitor/psmm/logs/rsyslog_mail_state.txt"
SERVICES = ["SQL", "FTP", "Web"]


def mariadb_query(requete):
    """Execute une requete SELECT via SSH avec le compte lecture seule."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=MARIADB["host"], username=MARIADB["user"],
                   key_filename=config.SSH_KEY)
    # -N : pas d'en-tete de colonnes. Compte lecture seule (psmm_reader).
    cmd = (f"mariadb -N -u psmm_reader -p'{config.DB_READER_PASSWORD}' "
           f"psmm -e \"{requete}\"")
    stdin, stdout, stderr = client.exec_command(cmd)
    sortie = stdout.read().decode()
    client.close()
    return sortie


def lire_dernier_id():
    try:
        with open(FICHIER_ETAT) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def ecrire_dernier_id(valeur):
    with open(FICHIER_ETAT, "w") as f:
        f.write(str(valeur))


def nouvelles_tentatives(apres_id):
    """Recupere les tentatives avec id > apres_id, triees par id."""
    req = (f"SELECT id, service, compte, ip, date_heure "
           f"FROM acces_errors WHERE id > {apres_id} ORDER BY id;")
    sortie = mariadb_query(req)
    lignes = []
    for l in sortie.splitlines():
        if l.strip():
            champs = l.split("\t")
            if len(champs) == 5:
                lignes.append(champs)  # [id, service, compte, ip, date]
    return lignes


def construire_corps(tentatives):
    """Met en forme en 3 sections (SQL/FTP/Web) + total, comme le Job 09."""
    corps = ["Rapport des NOUVELLES tentatives d'acces (collecte rsyslog)",
             "=" * 60, ""]
    total = 0
    for service in SERVICES:
        lignes_svc = [t for t in tentatives if t[1] == service]
        total += len(lignes_svc)
        corps.append(f"### {service} : {len(lignes_svc)} tentative(s)")
        if lignes_svc:
            corps.append(f"{'Compte':<20}{'Date/heure':<22}{'IP':<18}")
            corps.append("-" * 60)
            for (id_, svc, compte, ip, date_h) in lignes_svc:
                corps.append(f"{compte:<20}{date_h:<22}{ip:<18}")
        else:
            corps.append("(aucune)")
        corps.append("")
    corps.append("=" * 60)
    corps.append(f"TOTAL : {total} nouvelle(s) tentative(s).")
    return "\n".join(corps)


if __name__ == "__main__":
    dernier_id = lire_dernier_id()
    tentatives = nouvelles_tentatives(dernier_id)

    if tentatives:
        corps = construire_corps(tentatives)
        print(corps)
        envoyer_mail("[PSMM] Rapport rsyslog - nouvelles tentatives", corps)
        nouveau_dernier = int(tentatives[-1][0])  # id de la derniere ligne
        ecrire_dernier_id(nouveau_dernier)
        print(f"\n[+] Mail envoye ({len(tentatives)} nouvelles) - dernier id = {nouveau_dernier}")
    else:
        print("[*] Aucune nouvelle tentative - pas de mail")
