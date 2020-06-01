#!/bin/sh
find .git/objects/ -size 0 -delete
git fetch --all
git reset --hard origin/master
git rev-parse --short=7 HEAD > REVISION
echo 1 | tee /sys/class/leds/led0/brightness