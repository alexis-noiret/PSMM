#!/usr/bin/env python3
"""Job 14 - Met a jour les serveurs via Alcasar.
Pour chaque serveur (a tour de role, car Alcasar limite a 1 session/compte) :
auth Alcasar -> apt update/upgrade -> check reboot -> mail si reboot requis -> logout Alcasar."""

import sys
import paramiko

sys.path.append("/home/monitor/psmm")
import config
from mailer import envoyer_mail

A_METTRE_A_JOUR = ["ftp", "web", "mariadb"]

LOGOFF_URL = "https://alcasar.laplateforme.io:3991/logoff"


def ssh_exec(nom_serveur, commande, timeout=120):
    """Ouvre une connexion SSH, execute une commande, renvoie (sortie, erreur)."""
    srv = config.SERVEURS[nom_serveur]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=srv["host"], username=srv["user"],
                   key_filename=config.SSH_KEY, timeout=30)
    stdin, stdout, stderr = client.exec_command(commande, timeout=timeout)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    client.close()
    return sortie, erreur


def alcasar_login(nom_serveur):
    """Authentifie le serveur au portail Alcasar."""
    ssh_exec(nom_serveur, "bash ~/alcasar-login.sh > /dev/null 2>&1")


def alcasar_logout(nom_serveur):
    """Deconnecte le serveur d'Alcasar (libere le compte pour le suivant)."""
    ssh_exec(nom_serveur, f'curl -k -s "{LOGOFF_URL}" -o /dev/null')


def a_internet(nom_serveur):
    """Verifie que le serveur a bien acces a Internet."""
    sortie, _ = ssh_exec(nom_serveur, "ping -c1 -W3 8.8.8.8 > /dev/null 2>&1 && echo OK")
    return "OK" in sortie


def mettre_a_jour(nom_serveur):
    """apt update puis apt upgrade. Renvoie le resume."""
    ssh_exec(nom_serveur, "sudo apt update", timeout=180)
    sortie, _ = ssh_exec(nom_serveur, "sudo DEBIAN_FRONTEND=noninteractive apt -y upgrade",
                         timeout=600)
    return sortie


def reboot_requis(nom_serveur):
    """Verifie si un redemarrage est necessaire apres mise a jour."""
    sortie, _ = ssh_exec(nom_serveur, "test -f /var/run/reboot-required && echo OUI || echo NON")
    return "OUI" in sortie


if __name__ == "__main__":
    reboots = []   # serveurs necessitant un reboot

    for serveur in A_METTRE_A_JOUR:
        print(f"\n=== {serveur} ===")

        print("  [*] Authentification Alcasar...")
        alcasar_login(serveur)

        if not a_internet(serveur):
            print("  [!] Pas d'acces Internet apres auth - serveur ignore")
            alcasar_logout(serveur)
            continue
        print("  [+] Internet OK")

        print("  [*] Mise a jour (apt update + upgrade)...")
        mettre_a_jour(serveur)
        print("  [+] Mise a jour terminee")

        if reboot_requis(serveur):
            print("  [!] REDEMARRAGE REQUIS")
            reboots.append(serveur)
        else:
            print("  [*] Pas de redemarrage necessaire")

        print("  [*] Deconnexion Alcasar...")
        alcasar_logout(serveur)

    # mail a l'admin si au moins un serveur necessite un reboot
    if reboots:
        corps = ("Mise a jour des serveurs effectuee.\n\n"
                 "Les serveurs suivants necessitent un REDEMARRAGE :\n"
                 + "\n".join(f"  - {s}" for s in reboots))
        envoyer_mail("[PSMM] Redemarrage requis apres mise a jour", corps)
        print(f"\n[!] {len(reboots)} serveur(s) a redemarrer - mail envoye a l'admin")
    else:
        print("\n[*] Aucun redemarrage requis - pas de mail")
