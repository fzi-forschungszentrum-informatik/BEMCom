#!/bin/bash
#
# A simple script that saves the connector specific flows into json files to allow 
# versioning and backup of the connector.
#
# Change this to match the currently developed connector.
CONTAINER_NAME="homematic-connector"

# The flows are: 
#   "68dfd515.661f7c" - Specify available_datapoints
#   "219558b7.844058" - Receive raw_message
#   "545ec5f2.a5913c" - Parse raw_message
#   "9f1169a9.8e23c8" - Send command
FLOW_IDS=( "68dfd515.661f7c" "219558b7.844058" "545ec5f2.a5913c" "9f1169a9.8e23c8" )
for id in "${FLOW_IDS[@]}"
do
	echo "Processing flow $id"
    # if you want to pretty print the function code to add "| xargs -0 printf"
    docker exec "$CONTAINER_NAME" bash -c "curl localhost:1880/flow/$id/ | python -m json.tool " > "./flows/$id"
done
