#!/usr/bin/env python3
"""Job 15 - Notification Google Chat.
Deux modes (passes en argument) :
  - daily : rapport quotidien (etat systeme + resume des evenements)
  - check : surveillance ; alerte SEULEMENT si nouvelles tentatives detectees
            (dans ce cas, envoie l'alerte + l'etat systeme).
Usage : python3 ssh_chat.py [daily|check]"""

import sys
import re
from datetime import datetime
import paramiko

sys.path.append("/home/monitor/psmm")
import config
from chat_notifier import envoyer_chat

A_SURVEILLER = ["ftp", "web", "mariadb"]
MARIADB = config.SERVEURS["mariadb"]
FICHIER_ETAT = "/home/monitor/psmm/logs/chat_state.txt"
TABLES = {"SQL": "sql_errors", "FTP": "ftp_errors", "Web": "web_errors"}


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


def num(v):
    return float(v.replace(",", "."))


# ---------- Etat systeme ----------
def releve_cpu(s):
    o = ssh_exec(s, "top -bn2 -d 0.5 | grep '%Cpu' | tail -1")
    m = re.search(r"([\d,]+)\s*id", o)
    return round(100 - num(m.group(1)), 1) if m else 0.0


def releve_ram(s):
    o = ssh_exec(s, "free -m")
    for l in o.splitlines():
        if l.lower().startswith("mem") or l.startswith("Mém"):
            c = l.split()
            return round(num(c[2]) / num(c[1]) * 100, 1)
    return 0.0


def releve_disk(s):
    o = ssh_exec(s, "df -h /")
    for l in o.splitlines():
        if l.startswith("/dev/"):
            return num(l.split()[4].replace("%", ""))
    return 0.0


def bloc_etat_systeme():
    lignes = ["*Etat des serveurs :*"]
    for s in A_SURVEILLER:
        lignes.append(f"• *{s}* : CPU {releve_cpu(s)}% | RAM {releve_ram(s)}% | DISK {releve_disk(s)}%")
    return "\n".join(lignes)


# ---------- Evenements (tentatives d'acces) ----------
def total_tentatives():
    """Compte total des tentatives dans les 3 tables."""
    total = 0
    for table in TABLES.values():
        o = ssh_exec("mariadb", f'sudo mariadb -N -e "SELECT COUNT(*) FROM psmm.{table};"')
        try:
            total += int(o.strip())
        except ValueError:
            pass
    return total


def resume_evenements():
    lignes = ["*Tentatives d'acces frauduleuses :*"]
    for nom, table in TABLES.items():
        o = ssh_exec("mariadb", f'sudo mariadb -N -e "SELECT COUNT(*) FROM psmm.{table};"')
        lignes.append(f"• *{nom}* : {o.strip()} tentative(s)")
    return "\n".join(lignes)


# ---------- Etat persistant (dernier total vu + date rapport) ----------
def lire_etat():
    try:
        with open(FICHIER_ETAT) as f:
            date_rapport, dernier_total = f.read().strip().split(";")
            return date_rapport, int(dernier_total)
    except (FileNotFoundError, ValueError):
        return "", 0


def ecrire_etat(date_rapport, total):
    with open(FICHIER_ETAT, "w") as f:
        f.write(f"{date_rapport};{total}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    aujourdhui = datetime.now().strftime("%Y-%m-%d")
    heure = datetime.now().strftime("%d/%m/%Y %H:%M")

    date_rapport, dernier_total = lire_etat()
    total_actuel = total_tentatives()

    if mode == "daily":
        # rapport quotidien systematique
        msg = (f"📊 *Rapport quotidien PSMM* - {heure}\n\n"
               + bloc_etat_systeme() + "\n\n" + resume_evenements())
        envoyer_chat(msg)
        ecrire_etat(aujourdhui, total_actuel)
        print("[+] Rapport quotidien envoye")

    else:  # mode check : alerte seulement si nouvelles tentatives
        if total_actuel > dernier_total:
            nouvelles = total_actuel - dernier_total
            msg = (f"🚨 *ALERTE PSMM* - {nouvelles} nouvelle(s) tentative(s) detectee(s) - {heure}\n\n"
                   + resume_evenements() + "\n\n" + bloc_etat_systeme())
            envoyer_chat(msg)
            ecrire_etat(date_rapport, total_actuel)
            print(f"[!] Alerte envoyee ({nouvelles} nouvelles tentatives)")
        else:
            print("[*] Rien de nouveau - pas d'envoi")
