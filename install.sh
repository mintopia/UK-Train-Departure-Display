#!/bin/sh
apt install \
    libopenjp2-7 \
    libfreetype6-dev \
    libjpeg-dev \
    libtiff5 \
    python3-pip

pip3 install -r requirements.txt
cp ./departure-board.service /etc/systemd/system
cp ./departure-board-startup.service /etc/systemd/system

systemctl daemon-reload
systemctl enable departure-board-startup
systemctl enable departure-board
systemctl daemon-reload
systemctl start departure-board