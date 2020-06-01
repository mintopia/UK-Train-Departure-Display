#!/bin/sh
git fetch --all
git reset --hard origin/master
git rev-parse --short=7 HEAD > REVISION