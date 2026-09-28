#!/bin/bash
# Genere toutes les sorties terminal pour les captures de la soutenance.
# Lit les IP depuis config.py -> pas besoin de les coder en dur.

CFG=~/psmm/config.py
FTP=$(grep '"ftp"'     $CFG | grep -oP '\d+\.\d+\.\d+\.\d+')
WEB=$(grep '"web"'     $CFG | grep -oP '\d+\.\d+\.\d+\.\d+')
DB=$(grep '"mariadb"'  $CFG | grep -oP '\d+\.\d+\.\d+\.\d+')
PY=~/psmm-venv/bin/python3

echo "IP : ftp=$FTP web=$WEB mariadb=$DB"
pause(){ echo; echo "=== $1 ==="; echo; }

pause "JOB 01 - ssh root refuse (durcissement)"
ssh -o StrictHostKeyChecking=accept-new root@$FTP hostname 2>&1 | grep -i denied

pause "JOB 02 - outils installes"
python3 --version; mariadb --version; echo -n "ftp: "; which ftp; echo -n "lftp: "; which lftp

pause "JOB 03 - ssh_login.py (df distant)"
$PY ~/psmm/scripts/ssh_login.py

pause "JOB 04 - ssh_login_sudo.py (whoami -> root)"
$PY ~/psmm/scripts/ssh_login_sudo.py

pause "JOB 05 - ssh_mysql.py (SHOW DATABASES)"
$PY ~/psmm/scripts/ssh_mysql.py

pause "JOB 06 - generation + collecte SQL"
$PY ~/psmm/tools/generate_fake_attempts.py
$PY ~/psmm/scripts/ssh_mysql_error.py
ssh monitor@$DB 'sudo mariadb -e "SELECT * FROM psmm.sql_errors LIMIT 8;"'

pause "JOB 07 - table ftp_errors"
ssh monitor@$DB 'sudo mariadb -e "SELECT * FROM psmm.ftp_errors LIMIT 8;"'

pause "JOB 08 - table web_errors"
ssh monitor@$DB 'sudo mariadb -e "SELECT * FROM psmm.web_errors LIMIT 8;"'

pause "JOB 10 - backups horodates"
ssh monitor@$DB 'ls -1t ~/backups/ 2>/dev/null | head -8'

pause "JOB 11 - table system_status"
$PY ~/psmm/scripts/ssh_system_status.py
ssh monitor@$DB 'sudo mariadb -e "SELECT * FROM psmm.system_status ORDER BY id DESC LIMIT 6;"'

pause "JOB 13 - anti-spam (2 lancements)"
$PY ~/psmm/scripts/ssh_system_mail.py
echo "--- relance immediate ---"
$PY ~/psmm/scripts/ssh_system_mail.py

pause "JOB 14 - mise a jour via Alcasar"
$PY ~/psmm/scripts/ssh_update.py

echo; echo "=== TERMINE ==="
