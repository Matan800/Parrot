#!/bin/bash
CODE_DIR="/home/${FIRST_USER_NAME}/python"
SERVICE_FILE="/etc/systemd/system/parrot-systemd.service"
cat <<EOF >$SERVICE_FILE
# Parrot systemd-watchdog service file
[Unit]
Description=Parrot service
StartLimitBurst=5
StartLimitIntervalSec=600
After=multi-user.target

[Service]
User=${FIRST_USER_NAME}
WorkingDirectory=${CODE_DIR}
ExecStart=${CODE_DIR}/venv/bin/python -u ${CODE_DIR}/main_headless.py
KillSignal=SIGINT
Restart=on-failure
RestartSec=10
Type=notify
WatchdogSec=50

[Install]
WantedBy=multi-user.target
EOF
chmod 644 $SERVICE_FILE
systemctl enable parrot-systemd.service
