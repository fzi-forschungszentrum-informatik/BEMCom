if [ -d "./flows" ]
then
    # fnp is the full path of the file e.g. /flows/219558b7.844058
    # See https://nodered.org/docs/api/admin/methods/put/flow/ for API reference.
    for fnp in ./flows/*
    do
        flow_id=$( echo "$fnp" | rev | cut -d / -f 1 | rev )
        api_url="http://localhost:8205/flow/$flow_id"
        # Get the current flow definition from Node-RED
        flow=$(curl --silent -X GET $api_url)
        # Update the nodes with the exported flow information.
        # As of Node-RED 1.0.3 this has the same format as the exportet flow. 
        # The exportet version has an additional meta information object that is 
        # ignored while updating the flow.
        flow=$(echo "$flow" | jq ".nodes = $(cat $fnp)")
        curl --silent -X PUT -H "Content-Type: application/json" --data "$flow" "$api_url" > /dev/null
        echo "updated flow $flow_id"
    done
fi
