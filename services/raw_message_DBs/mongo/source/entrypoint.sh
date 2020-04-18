#!/bin/bash

# TODO: The kill commands are not executed, it seems as the variable with the pid is empty.

# Patches SIGTERM and SIGINT to stop background processes.
# This is required for processes to gracefully shutdown if docker
# wants to stop the container.
trap "kill -TERM $mongo_pid" SIGTERM
trap "kill -TERM $mqtt_integration_pid" SIGTERM
#trap "kill -INT $mongo_pid" INT
#trap "kill -INT $mqtt_integration_pid" INT

mongod &
mongo_pid=$!

# Boot the DB before connecting with MQTT.
sleep 3

python3 /bemcom/mqtt_integration.py &
mqtt_integration_pid=$!


# Run processes until the container is stopped, also give proceses some time after receiving
# SIGTERM to gracefully.
wait
sleep 2
