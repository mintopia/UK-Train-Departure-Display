#!/bin/sh
apt install \
    ibopenjp2-7 \
    libfreetype6-dev \
    libjpeg-dev \
    libtiff5 \
    python3-pip

pip install -r requirements.txt