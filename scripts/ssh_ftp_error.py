#!/usr/bin/env python3
"""Job 07 - Collecte les tentatives d'acces FTP echouees et les stocke en base.
Lit les logs vsftpd (PAM) sur le serveur ftp, insere sur le serveur mariadb.
Script de supervision."""

import sys
import re
import paramiko

sys.path.append("/home/monitor/psmm")
import config


def ssh_exec(nom_serveur, commande):
    """Ouvre une connexion SSH au serveur demande et execute une commande."""
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
    """Lit les logs vsftpd et extrait date, compte (ruser) et IP (rhost)."""
    cmd = ("sudo journalctl -u vsftpd -o short-iso --no-pager "
           "| grep 'authentication failure'")
    sortie, _ = ssh_exec("ftp", cmd)

    erreurs = []
    # Exemple : 2026-09-17T09:40:50+02:00 ... ruser=baduser rhost=::ffff:127.0.0.1
    motif = re.compile(
        r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}).*?"
        r"ruser=(\S+).*?rhost=(\S+)"
    )
    for ligne in sortie.splitlines():
        m = motif.search(ligne)
        if m:
            date, heure, compte, ip = m.group(1), m.group(2), m.group(3), m.group(4)
            # nettoie l'IPv6-mapped ::ffff:127.0.0.1 -> 127.0.0.1
            if ip.startswith("::ffff:"):
                ip = ip.replace("::ffff:", "")
            erreurs.append({
                "date_heure": f"{date} {heure}",
                "compte": compte,
                "ip": ip,
            })
    return erreurs


def inserer_erreurs(erreurs):
    """Insere les erreurs dans psmm.ftp_errors sur le serveur mariadb."""
    inserees = 0
    for e in erreurs:
        requete = (
            "INSERT IGNORE INTO psmm.ftp_errors (compte, date_heure, ip) "
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
    print(f"[*] {len(erreurs)} tentatives FTP trouvees dans les logs")
    inserer_erreurs(erreurs)
