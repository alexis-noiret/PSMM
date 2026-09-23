#!/usr/bin/env python3
"""Job 08 - Collecte les tentatives d'acces web (auth basic) echouees.
Lit error.log d'Apache sur le serveur web, insere sur mariadb. Supervision."""

import sys
import re
from datetime import datetime
import paramiko

sys.path.append("/home/monitor/psmm")
import config


def ssh_exec(nom_serveur, commande):
    srv = config.SERVEURS[nom_serveur]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=srv["host"], username=srv["user"],
                   key_filename=config.SSH_KEY)
    stdin, stdout, stderr = client.exec_command(commande)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()
    return sortie, erreur


def parser_erreurs():
    """Lit error.log Apache et extrait date, compte et IP des echecs d'auth."""
    cmd = "sudo grep -E 'AH01618|AH01617' /var/log/apache2/error.log"
    sortie, _ = ssh_exec("web", cmd)

    erreurs = []
    motif = re.compile(
        r"\[(\w{3} \w{3} +\d+ \d{2}:\d{2}:\d{2})\.\d+ (\d{4})\].*?"
        r"\[client ([\d.]+):\d+\].*?user (\S+)"
    )
    for ligne in sortie.splitlines():
        m = motif.search(ligne)
        if m:
            date_brute, annee, ip, compte = m.groups()
            compte = compte.rstrip(":")
            dt = datetime.strptime(f"{date_brute} {annee}", "%a %b %d %H:%M:%S %Y")
            date_heure = dt.strftime("%Y-%m-%d %H:%M:%S")
            erreurs.append({
                "date_heure": date_heure,
                "compte": compte,
                "ip": ip,
            })
    return erreurs


def inserer_erreurs(erreurs):
    inserees = 0
    for e in erreurs:
        requete = (
            "INSERT IGNORE INTO psmm.web_errors (compte, date_heure, ip) "
            f"VALUES ('{e['compte']}', '{e['date_heure']}', '{e['ip']}'); "
            "SELECT ROW_COUNT();"
        )
        sortie, _ = ssh_exec("mariadb", f'sudo mariadb -N -e "{requete}"')
        if sortie.strip() == "1":
            inserees += 1
    ignorees = len(erreurs) - inserees
    print(f"[+] {inserees} nouvelles erreurs inserees, {ignorees} doublons ignores")


if __name__ == "__main__":
    erreurs = parser_erreurs()
    print(f"[*] {len(erreurs)} tentatives web trouvees dans les logs")
    inserer_erreurs(erreurs)
