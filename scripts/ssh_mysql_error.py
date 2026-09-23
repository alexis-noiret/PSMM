#!/usr/bin/env python3
"""Job 06 - Collecte les tentatives d'acces MariaDB echouees et les stocke en base.
Lit les logs existants (quelle que soit l'origine) - script de supervision."""

import sys
import re
import paramiko

sys.path.append("/home/monitor/psmm")
import config

SRV = config.SERVEURS["mariadb"]


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


def recuperer_ip_client():
    sortie, _ = ssh_exec("echo $SSH_CLIENT")
    return sortie.split()[0] if sortie else "inconnue"


def parser_erreurs():
    cmd = "sudo journalctl -u mariadb --no-pager | grep 'Access denied'"
    sortie, _ = ssh_exec(cmd)

    erreurs = []
    motif = re.compile(
        r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}:\d{2}).*?"
        r"Access denied for user '([^']+)'"
    )
    for ligne in sortie.splitlines():
        m = motif.search(ligne)
        if m:
            date, heure, compte = m.group(1), m.group(2), m.group(3)
            heure = ":".join(x.zfill(2) for x in heure.split(":"))
            erreurs.append({"date_heure": f"{date} {heure}", "compte": compte})
    return erreurs


def inserer_erreurs(erreurs, ip):
    inserees = 0
    for e in erreurs:
        requete = (
            "INSERT IGNORE INTO psmm.sql_errors (compte, date_heure, ip) "
            f"VALUES ('{e['compte']}', '{e['date_heure']}', '{ip}'); "
            "SELECT ROW_COUNT();"
        )
        sortie, _ = ssh_exec(f'sudo mariadb -N -e "{requete}"')
        # ROW_COUNT() renvoie 1 si insere, 0 si ignore (doublon)
        if sortie.strip() == "1":
            inserees += 1
    ignorees = len(erreurs) - inserees
    print(f"[+] {inserees} nouvelles erreurs inserees, {ignorees} doublons ignores")


if __name__ == "__main__":
    ip = recuperer_ip_client()
    print(f"[*] IP source : {ip}")

    erreurs = parser_erreurs()
    print(f"[*] {len(erreurs)} tentatives trouvees dans les logs")

    inserer_erreurs(erreurs, ip)
