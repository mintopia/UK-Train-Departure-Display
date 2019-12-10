#!/bin/bash

export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket

# Optional step - it takes couple of seconds (or longer) to establish a WiFi connection
# sometimes. In this case, following checks will fail and wifi-connect
# will be launched even if the device will be able to connect to a WiFi network.
# If this is your case, you can wait for a while and then check for the connection.
# sleep 15

# Choose a condition for running WiFi Connect according to your use case:

# 1. Is there a default gateway?
ip route | grep default

# 2. Is there Internet connectivity?
# nmcli -t g | grep full

# 3. Is there Internet connectivity via a google ping?
# wget --spider http://google.com 2>&1

# 4. Is there an active WiFi connection?
# iwgetid -r

if [ $? -eq 0 ]; then
    echo 'Skipping WiFi Connect\n'
else
    echo 'Starting WiFi Connect\n'
    ./wifi-connect
fi

cp config.sample.json config.json
jq .journey.departureStation=\""${departure:=STP}"\" config.json | sponge config.json
jq .journey.destinationStation=\""${destination:=}"\" config.json | sponge config.json
jq .journey.platform=\""${platform:=}"\" config.json | sponge config.json
jq .refreshTime="${refreshTime:=120}" config.json | sponge config.json
jq .fps="${fps:=10}" config.json | sponge config.json
jq .brightness="${brightness:=255}" config.json | sponge config.json
jq .powersaving.brightness="${powersavingBrightness:=25}" config.json | sponge config.json
jq .powersaving.start="${powersavingStart:=0}" config.json | sponge config.json
jq .powersaving.end="${powersavingEnd:=6}" config.json | sponge config.json
jq .api.username=\""${apiUsername}"\" config.json | sponge config.json
jq .api.password=\""${apiPassword}"\" config.json | sponge config.json

echo 'Config:'
cat config.json

echo 'Starting App'
python ./src/main.py
