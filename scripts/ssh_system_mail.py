#!/usr/bin/env python3
"""Job 12+13 - Releve l'etat systeme des serveurs, le stocke, et alerte l'admin
par mail si un seuil est depasse (un seul mail recapitulatif par cycle).
Job 13 : limite a un mail par heure maximum.
Prevu pour tourner en cron toutes les 5 min."""

import sys
import os
import re
from datetime import datetime, timedelta
import paramiko

sys.path.append("/home/monitor/psmm")
import config
from mailer import envoyer_mail

# ============================================================
# SEUILS D'ALERTE - facilement modifiables ici
SEUIL_CPU = 70    # %
SEUIL_DISK = 90   # %
SEUIL_RAM = 80    # %
# ============================================================

A_SURVEILLER = ["ftp", "web", "mariadb"]
RETENTION_HEURES = 72

# Fichier memorisant l'heure du dernier mail envoye (limite 1 mail/heure)
FICHIER_DERNIER_MAIL = "/home/monitor/psmm/logs/last_mail.txt"
DELAI_MIN_MAIL = timedelta(hours=1)


def ssh_exec(nom_serveur, commande):
    srv = config.SERVEURS[nom_serveur]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=srv["host"], username=srv["user"],
                   key_filename=config.SSH_KEY)
    stdin, stdout, stderr = client.exec_command(commande)
    sortie = stdout.read().decode()
    client.close()
    return sortie


def num(valeur):
    return float(valeur.replace(",", "."))


def releve_cpu(nom_serveur):
    sortie = ssh_exec(nom_serveur, "top -bn2 -d 0.5 | grep '%Cpu' | tail -1")
    m = re.search(r"([\d,]+)\s*id", sortie)
    if m:
        return round(100 - num(m.group(1)), 1)
    return 0.0


def releve_ram(nom_serveur):
    sortie = ssh_exec(nom_serveur, "free -m")
    for ligne in sortie.splitlines():
        if ligne.lower().startswith("mem") or ligne.startswith("Mém"):
            champs = ligne.split()
            return round(num(champs[2]) / num(champs[1]) * 100, 1)
    return 0.0


def releve_disk(nom_serveur):
    sortie = ssh_exec(nom_serveur, "df -h /")
    for ligne in sortie.splitlines():
        if ligne.startswith("/dev/"):
            return num(ligne.split()[4].replace("%", ""))
    return 0.0


def inserer(serveur, cpu, ram, disk):
    requete = (
        "INSERT INTO psmm.system_status (serveur, cpu_pct, ram_pct, disk_pct, releve_le) "
        f"VALUES ('{serveur}', {cpu}, {ram}, {disk}, NOW());"
    )
    ssh_exec("mariadb", f'sudo mariadb -e "{requete}"')


def purger_anciennes():
    requete = (
        "DELETE FROM psmm.system_status "
        f"WHERE releve_le < NOW() - INTERVAL {RETENTION_HEURES} HOUR;"
    )
    ssh_exec("mariadb", f'sudo mariadb -e "{requete}"')


def verifier_seuils(serveur, cpu, ram, disk):
    alertes = []
    if cpu > SEUIL_CPU:
        alertes.append(f"  - CPU : {cpu}% (seuil {SEUIL_CPU}%)")
    if ram > SEUIL_RAM:
        alertes.append(f"  - RAM : {ram}% (seuil {SEUIL_RAM}%)")
    if disk > SEUIL_DISK:
        alertes.append(f"  - DISK : {disk}% (seuil {SEUIL_DISK}%)")
    return alertes


def mail_autorise():
    """Renvoie True si le dernier mail date de plus d'une heure (ou jamais)."""
    if not os.path.exists(FICHIER_DERNIER_MAIL):
        return True
    with open(FICHIER_DERNIER_MAIL) as f:
        dernier = datetime.fromisoformat(f.read().strip())
    return datetime.now() - dernier >= DELAI_MIN_MAIL


def noter_envoi():
    """Enregistre l'heure de l'envoi courant."""
    with open(FICHIER_DERNIER_MAIL, "w") as f:
        f.write(datetime.now().isoformat())


if __name__ == "__main__":
    depassements = []

    for serveur in A_SURVEILLER:
        cpu = releve_cpu(serveur)
        ram = releve_ram(serveur)
        disk = releve_disk(serveur)
        inserer(serveur, cpu, ram, disk)
        print(f"[+] {serveur:<10} CPU={cpu}%  RAM={ram}%  DISK={disk}%")

        alertes = verifier_seuils(serveur, cpu, ram, disk)
        if alertes:
            depassements.append(f"Serveur {serveur} :\n" + "\n".join(alertes))

    purger_anciennes()

    if depassements:
        if mail_autorise():
            corps = ("ALERTE - Seuils systeme depasses\n"
                     + "=" * 40 + "\n\n"
                     + "\n\n".join(depassements))
            envoyer_mail("[PSMM] ALERTE seuils systeme", corps)
            noter_envoi()
            print(f"\n[!] {len(depassements)} serveur(s) en depassement - mail envoye")
        else:
            print(f"\n[!] {len(depassements)} serveur(s) en depassement - "
                  "mail deja envoye il y a moins d'1h, pas de nouvel envoi")
    else:
        print("\n[*] Aucun depassement - pas de mail")
