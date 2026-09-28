#!/usr/bin/env python3
"""Job 15 - Notification Google Chat.
- daily : rapport quotidien (etat systeme + total des tentatives)
- check : alerte SEULEMENT sur les NOUVELLES tentatives (detail id/compte/date/IP)
          suivi du dernier id vu par table dans un fichier memoire.
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
# nom lisible -> table
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
            c = l.split(); return round(num(c[2]) / num(c[1]) * 100, 1)
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


# ---------- Etat persistant : dernier id vu par table ----------
def lire_etat():
    """Retourne un dict {table: dernier_id} + la date du dernier rapport."""
    ids = {t: 0 for t in TABLES.values()}
    date_rapport = ""
    try:
        with open(FICHIER_ETAT) as f:
            for ligne in f.read().strip().splitlines():
                if ligne.startswith("rapport="):
                    date_rapport = ligne.split("=", 1)[1]
                elif "=" in ligne:
                    t, v = ligne.split("=", 1)
                    if t in ids:
                        ids[t] = int(v)
    except (FileNotFoundError, ValueError):
        pass
    return date_rapport, ids

def ecrire_etat(date_rapport, ids):
    with open(FICHIER_ETAT, "w") as f:
        f.write(f"rapport={date_rapport}\n")
        for t, v in ids.items():
            f.write(f"{t}={v}\n")


def dernier_id(table):
    """Plus grand id actuellement en base pour cette table."""
    o = ssh_exec("mariadb", f'sudo mariadb -N -e "SELECT IFNULL(MAX(id),0) FROM psmm.{table};"')
    try:
        return int(o.strip())
    except ValueError:
        return 0

def nouvelles_lignes(table, apres_id):
    """Renvoie les lignes de la table avec id > apres_id (les nouvelles)."""
    req = (f"SELECT id, compte, date_heure, ip FROM psmm.{table} "
           f"WHERE id > {apres_id} ORDER BY id;")
    o = ssh_exec("mariadb", f'sudo mariadb -N -e "{req}"')
    lignes = []
    for l in o.splitlines():
        if l.strip():
            champs = l.split("\t")
            if len(champs) == 4:
                lignes.append(champs)  # [id, compte, date, ip]
    return lignes

def total(table):
    o = ssh_exec("mariadb", f'sudo mariadb -N -e "SELECT COUNT(*) FROM psmm.{table};"')
    try:
        return int(o.strip())
    except ValueError:
        return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    aujourdhui = datetime.now().strftime("%Y-%m-%d")
    heure = datetime.now().strftime("%d/%m/%Y %H:%M")

    date_rapport, ids_vus = lire_etat()

    if mode == "daily":
        # rapport quotidien : etat systeme + TOTAL (vue d'ensemble)
        lignes = [f"📊 *Rapport quotidien PSMM* - {heure}", "", bloc_etat_systeme(), "",
                  "*Total des tentatives archivees :*"]
        for nom, table in TABLES.items():
            lignes.append(f"• *{nom}* : {total(table)} tentative(s)")
        envoyer_chat("\n".join(lignes))
        # on met a jour la date rapport ET les id (pour repartir propre)
        for t in TABLES.values():
            ids_vus[t] = dernier_id(t)
        ecrire_etat(aujourdhui, ids_vus)
        print("[+] Rapport quotidien envoye")

    else:  # check : alerte seulement sur les NOUVELLES tentatives, avec detail
        blocs = []
        total_nouvelles = 0
        for nom, table in TABLES.items():
            lignes_new = nouvelles_lignes(table, ids_vus[table])
            if lignes_new:
                total_nouvelles += len(lignes_new)
                sous = [f"*{nom}* — {len(lignes_new)} nouvelle(s) :"]
                for (id_, compte, date_h, ip) in lignes_new:
                    sous.append(f"   • #{id_} `{compte}` — {date_h} — {ip}")
                blocs.append("\n".join(sous))
                # on avance le dernier id vu pour cette table
                ids_vus[table] = int(lignes_new[-1][0])

        if total_nouvelles > 0:
            msg = (f"🚨 *ALERTE PSMM* — {total_nouvelles} nouvelle(s) tentative(s) — {heure}\n\n"
                   + "\n\n".join(blocs))
            envoyer_chat(msg)
            ecrire_etat(date_rapport, ids_vus)
            print(f"[!] Alerte envoyee ({total_nouvelles} nouvelles)")
        else:
            print("[*] Rien de nouveau - pas d'envoi")
