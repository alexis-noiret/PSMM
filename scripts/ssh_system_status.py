#!/usr/bin/env python3
"""Job 11 - Releve l'etat systeme (CPU/RAM/DISK) des serveurs et le stocke en base.
Ne conserve que les 72 dernieres heures."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config

MARIADB = config.SERVEURS["mariadb"]
# serveurs a surveiller (les 3 serveurs, pas le client)
A_SURVEILLER = ["ftp", "web", "mariadb"]
RETENTION_HEURES = 72


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
    """Convertit un nombre en format francais (virgule) vers float."""
    return float(valeur.replace(",", "."))


def releve_cpu(nom_serveur):
    """CPU utilise = 100 - idle. Prend la 2e passe de top (plus fiable)."""
    # -bn2 : 2 iterations, on garde la derniere ligne %Cpu (mesure stable)
    sortie = ssh_exec(nom_serveur, "top -bn2 -d 0.5 | grep '%Cpu' | tail -1")
    # exemple : %Cpu(s):  0,0 ut,  9,1 sy, ..., 90,9 id, ...
    # on isole la valeur idle : le nombre juste avant 'id'
    import re
    m = re.search(r"([\d,]+)\s*id", sortie)
    if m:
        idle = num(m.group(1))
        return round(100 - idle, 1)
    return 0.0


def releve_ram(nom_serveur):
    """RAM utilisee en % = utilise / total * 100. Lit la ligne Mem de free."""
    sortie = ssh_exec(nom_serveur, "free -m")
    for ligne in sortie.splitlines():
        # la ligne memoire commence par Mem: (ou Mém: selon locale)
        if ligne.lower().startswith("mem") or ligne.startswith("Mém"):
            champs = ligne.split()
            total = num(champs[1])
            utilise = num(champs[2])
            return round(utilise / total * 100, 1)
    return 0.0


def releve_disk(nom_serveur):
    """Disque utilise en % sur la partition racine. Lit df -h /."""
    sortie = ssh_exec(nom_serveur, "df -h /")
    for ligne in sortie.splitlines():
        if ligne.startswith("/dev/"):
            champs = ligne.split()
            # le % est le 5e champ (ex: 18%)
            return num(champs[4].replace("%", ""))
    return 0.0


def inserer(serveur, cpu, ram, disk):
    requete = (
        "INSERT INTO psmm.system_status (serveur, cpu_pct, ram_pct, disk_pct, releve_le) "
        f"VALUES ('{serveur}', {cpu}, {ram}, {disk}, NOW());"
    )
    ssh_exec("mariadb", f'sudo mariadb -e "{requete}"')


def purger_anciennes():
    """Supprime les releves de plus de RETENTION_HEURES heures."""
    requete = (
        "DELETE FROM psmm.system_status "
        f"WHERE releve_le < NOW() - INTERVAL {RETENTION_HEURES} HOUR;"
    )
    ssh_exec("mariadb", f'sudo mariadb -e "{requete}"')


if __name__ == "__main__":
    for serveur in A_SURVEILLER:
        cpu = releve_cpu(serveur)
        ram = releve_ram(serveur)
        disk = releve_disk(serveur)
        inserer(serveur, cpu, ram, disk)
        print(f"[+] {serveur:<10} CPU={cpu}%  RAM={ram}%  DISK={disk}%")

    purger_anciennes()
    print(f"[*] Releves de plus de {RETENTION_HEURES}h purges")
