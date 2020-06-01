#!/bin/sh
apt install \
    ibopenjp2-7 \
    libfreetype6-dev \
    libjpeg-dev \
    libtiff5 \
    python3-pip

pip install -r requirements.txt
cp ./departure-board.service /etc/systemd/service
cp ./departure-board-startup.service /etc/systemd/service

systemctl reload
systemctl install departure-board-startup
systemctl install departure-board
systemctl start depature-board-startup
systemctl start departure-board