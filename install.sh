#!/bin/sh
apt install \
    ibopenjp2-7 \
    libfreetype6-dev \
    libjpeg-dev \
    libtiff5 \
    python3-pip

pip install -r requirements.txt
cp ./departure-board.service /etc/systemd/system
cp ./departure-board-startup.service /etc/systemd/system

systemctl daemon-reload
systemctl enable departure-board-startup
systemctl enable departure-board
systemctl start departure-board