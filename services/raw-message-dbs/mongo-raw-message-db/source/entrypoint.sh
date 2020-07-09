#!/bin/bash

# Start the DB in background.
if [ -z $MONGO_USERNAME ]
then
    # No auth if username is not set.
    mongod --bind_ip_all &
else
    mongod --auth --bind_ip_all &
fi
mongo_pid=$!

# Give the DB time to boot before connecting with MQTT.
sleep 3

# Connect the DB to MQTT.
python3 /bemcom/mqtt_integration.py &
mqtt_integration_pid=$!

# Patch SIGTERM and SIGINT to the child processes, to allow them to shutdown 
# gracefully if the container shuts down. Shutdown MQTT integration first so it
# can finish a potential write process before we unplug the DB.
trap "kill -INT $mqtt_integration_pid && sleep 1 && kill -INT $mongo_pid" SIGINT
trap "kill -TERM $mqtt_integration_pid && sleep 1 && kill -TERM $mongo_pid" SIGTERM

# Wait for the childprocesses to terminate, that will should happen only on error
# or if the container is shut down.
wait $mqtt_integration_pid
wait $mongo_pid
