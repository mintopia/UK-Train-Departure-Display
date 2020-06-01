#!/bin/sh
git fetch --all
git reset --hard origin/master
git rev-parse --short=7 HEAD > REVISION
echo 1 | tee /sys/class/leds/led0/brightness