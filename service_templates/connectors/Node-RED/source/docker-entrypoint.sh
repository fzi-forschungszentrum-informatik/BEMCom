#!/bin/bash
echo "docker-entrypoint.sh: Starting up"

# Populates the environment variables for the MQTT topics according to the topic convention
# specified in the message format documentation.
echo "docker-entrypoint.sh: Populating environment varables for connector: ${CONNECTOR_NAME}"
export MQTT_TOPIC_LOGS="${CONNECTOR_NAME}/logs"
export MQTT_TOPIC_HEARTBEAT="${CONNECTOR_NAME}/heartbeat"
export MQTT_TOPIC_AVAILABLE_DATAPOINTS="${CONNECTOR_NAME}/available_datapoints"
export MQTT_TOPIC_DATAPOINT_MAP="${CONNECTOR_NAME}/datapoint_map"
export MQTT_TOPIC_RAW_MESSAGE_TO_DB="${CONNECTOR_NAME}/raw_message_to_db"
export MQTT_TOPIC_RAW_MESSAGE_REPROCESS="${CONNECTOR_NAME}/raw_message_reprocess"
export MQTT_TOPIC_DATAPOINT_MESSAGE_WILDCARD="${CONNECTOR_NAME}/messages/#"

# Starts Node-RED in a background process.
echo "docker-entrypoint.sh: Starting Node-RED"
cd /usr/src/node-red
npm start -- --userDir /data &
node_red_pid=$!

# Patches SIGTERM and SIGINT to stop background Node-RED.
# This is required for Node-RED to gracefully shutdown if docker
# wants to stop the container.
trap "kill -TERM $node_red_pid" SIGTERM
trap "kill -INT $node_red_pid" INT

# Write the stored flows into the running Node-RED instance.
sleep 5
if [ -d "/flows" ]
then
    # fnp is the full path of the file e.g. /flows/219558b7.844058
    # See https://nodered.org/docs/api/admin/methods/put/flow/ for API reference.
    for fnp in /flows/*
    do
        flow_id=$( echo "$fnp" | rev | cut -d / -f 1 | rev )
        if [ "$flow_id" = "Readme.md" ]
        then
            continue
        fi

        api_url="http://localhost:1880/flow/$flow_id"
        # Get the current flow definition from Node-RED
        flow=$(curl --silent -X GET $api_url)
        # Update the nodes with the exported flow information.
        # As of Node-RED 1.0.3 this has the same format as the exportet flow. 
        # The exportet version has an additional meta information object that is 
        # ignored while updating the flow.
        flow=$(echo "$flow" | jq ".nodes = $(cat $fnp)")
        curl --silent -X PUT -H "Content-Type: application/json" --data "$flow" "$api_url" > /dev/null
        echo "docker-entrypoint.sh: Updated flow $flow_id"
    done
else
    echo "docker-entrypoint.sh: Found no files in /flows"
fi

# Run Node-RED until the container is stopped, also give Node-RED some time after receiving
# SIGTERM to shutdown flows and connections.
wait
sleep 2
