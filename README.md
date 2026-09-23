cat > ~/psmm/README.md << 'EOF'
# PSMM — Sous-système de supervision de sécurité

Projet d'infrastructure et de supervision (Python, Shell, MariaDB, Mail) — La Plateforme.

## Objectif

Récupérer les logs des serveurs FTP, SQL et Web, archiver les tentatives d'accès
frauduleuses dans une base de données, et alerter l'administrateur par mail et
Google Chat.

## Architecture

- **pokemon_client** — poste de supervision (Python), pilote les serveurs en SSH
- **pokemon_ftp** — serveur FTP (vsftpd)
- **pokemon_web** — serveur Web (Apache + authentification basic)
- **pokemon_mariadb** — serveur SQL (MariaDB) + base centrale `psmm`

Les 4 VM Debian 13 sont sur le réseau de la plateforme (bridge, portail Alcasar).

## Sécurité

- Accès SSH par clé uniquement, root interdit, seul le compte `monitor` autorisé
- `sudo` granulaire via `/etc/sudoers.d/` (NOPASSWD limité aux commandes nécessaires)
- Secrets isolés dans `.env` (jamais commité)

## Structure du dépôt

- `config.py` — configuration centrale (IP, chemins ; secrets via `.env`)
- `mailer.py` / `chat_notifier.py` — modules d'envoi mail et Google Chat
- `scripts/` — les livrables (scripts de supervision `ssh_*.py`)
- `tools/` — utilitaires de test (génération de fausses tentatives)

## Les scripts (Jobs)

| Script | Rôle |
|--------|------|
| ssh_login.py | Connexion SSH + commande distante |
| ssh_login_sudo.py | Idem en sudo |
| ssh_mysql.py | Accès au serveur MariaDB |
| ssh_mysql_error.py | Collecte des tentatives SQL échouées |
| ssh_ftp_error.py | Collecte des tentatives FTP échouées |
| ssh_web_error.py | Collecte des tentatives Web échouées |
| ssh_serveur_mail.py | Rapport mail des tentatives de la veille |
| ssh_cron_backup.py | Sauvegarde de la base (rétention 7) |
| ssh_system_status.py | Relevé CPU/RAM/DISK (rétention 72h) |
| ssh_system_mail.py | Alerte mail si seuils dépassés |
| ssh_update.py | Mise à jour des serveurs via Alcasar |
| ssh_chat.py | Notification Google Chat (rapport + alertes) |

## Installation

    python3 -m venv psmm-venv
    source psmm-venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env

## Planification (cron)

- Sauvegarde : toutes les 3h
- Monitoring + alertes seuils : toutes les 5 min
- Rapport Google Chat : quotidien a 8h
- Surveillance Google Chat : toutes les 5 min
