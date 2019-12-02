# Setting 

* MQTT Broker as central communication interface
* Mongo DB to store raw messages.
* Abstraction of devices and data sources as datapoints. One point per value.
* First define a flow, the general process of how the data is handled on a high level, then next fill the flow with live (as generic as possible)

# TODO

* Add general usage instructions to this file
* Remove the Devl stuff flow
* May convert the Devl stuff into a test flow?

# Process to derive Connectors

### Copy and modify files

* Pick a meaningful connector name. Use only lowercase letters, numbers and dashes (for the docker internal name resolution system to work.) The connector name should end with `connector`, e.g. `my-demo-connector`. Create a folder with the connector name.

* Copy content of this folder  inside the new folder, ignore Readme files.

* Modify .env file:

  * Change the value for `CONNECTOR_NAME` to the connector name, E.g. 

    ```
    CONNECTOR_NAME=my-demo-connector
    ```

  * If required change the Node-RED development port `NODE_RED_PORT` to a free port on your local machine.

  * Check your local user id and group id (with `id -u` and `id -g`) and change the values accordingly. This is required to ensure that the container runs with your permissions, and files created by Node-RED will be accessible to you too. E.g. if your user-id is 1002 and group-id 1004 change the entries as follows:

    ```
    USER_ID=1002
    GROUP_ID=1004
    ```

    

  * Add default values for additional environment variables you may require.  Your `.env` file should no look like:

    ```
    # Both these values should be unique on a host.
    # CONTAINER_NAME should be all lower case and use only dashes as additional char 
    # (no underscore or space) as it is also used for internal name resolution within 
    # the docker network and within MQTT topics.
    CONNECTOR_NAME=my-demo-connector
    NODE_RED_PORT=8201
    
    # Use id -u and id -g on linux to find your current user/group id.
    USER_ID=1002
    GROUP_ID=1004
    
    # Update this tag to the latest version before starting a new connector.
    NODE_RED_TAG=1.0.2
    
    # Message broker settings. Use the mqtt_broker_credentials.env file
    # to set username and password for the broker.
    MQTT_BROKER_HOST=message-broker
    MQTT_BROKER_PORT=1883
    
    # Will send all raw messages over MQTT too if set to TRUE
    SEND_RAW_MESSAGE_TO_DB=TRUE
    
    # Demo connector specific environment variables
    DEMO_URL=http://example.org
    ```

* If secrets (e.g. login credentials) are required, create a file with filename `secrets.env` . Ensure that`secrets.env` is not checked in to version control. Place all secret values there e.g. like: 

  ```
  USERNAME=my-user-name
  PASSWORD=my-secert-password
  ```

* Modify the `docker-compose.devl.yml` file.

  * Change the service name from `node-red-connector-template` to your chosen CONNECTOR_NAME.

  * If secrets are required, add the following lines to the service definition  `docker-compose.devl.yml` file: 

    ```
            # Load credentials.
            env_file:
                - secrets.env
    ```

  * Add the environment variables you wish to expose to Node-RED in the environment section. e.g.

  * The resulting docker-compose.devl.yml file could no look like:

    ```
    version: '3'
    
    services:
    
        # This should be unique and as best practice identical to ${CONNECTOR_NAME}
        my-demo-connector:
    
            container_name: ${CONNECTOR_NAME}
    
            ports:
                - ${NODE_RED_PORT}:1880
    
            # Slightly modified version of the default node-red image
            # to ensure that Node-RED writes it's files with the 
            # user_id/group_id that is configured below. 
            build:
                context: .
                dockerfile: Dockerfile_Node-RED_with_custom_user_id
                args: 
                    - USER_ID=${USER_ID}
                    - GROUP_ID=${GROUP_ID}
                    - NODE_RED_TAG=${NODE_RED_TAG}
    
            volumes: 
                - ./Node-RED_data:/data
    
            restart: always
    
            # Load credentials.
            env_file:
                - secrets.env
    
            # Pass connector configuration in container.
            # See additional documentation and default values in .env file
            environment:
                - CONNECTOR_NAME=${CONNECTOR_NAME}
                - MQTT_BROKER_HOST=${MQTT_BROKER_HOST}
                - MQTT_BROKER_PORT=${MQTT_BROKER_PORT}
                - MQTT_TOPIC_LOGS=${CONNECTOR_NAME}/logs
                - MQTT_TOPIC_HEARTBEAT=${CONNECTOR_NAME}/heartbeat
                - MQTT_TOPIC_AVAILABLE_DATAPOINTS=${CONNECTOR_NAME}/available_datapoints
                - MQTT_TOPIC_DATAPOINT_MAP=${CONNECTOR_NAME}/datapoint_map
                - MQTT_TOPIC_RAW_MESSAGE_TO_DB=${CONNECTOR_NAME}/raw_message_to_db
                - MQTT_TOPIC_RAW_MESSAGE_REPROCESS=${CONNECTOR_NAME}/raw_message_reprocess
                - MQTT_TOPIC_DATAPOINT_MESSAGE_WILDCARD=${CONNECTOR_NAME}/messages/#
                - SEND_RAW_MESSAGE_TO_DB=${SEND_RAW_MESSAGE_TO_DB}
    
        message-broker:
            container_name: message-broker
            image: "eclipse-mosquitto:1.5.4"
            user: "${USER_ID}:${GROUP_ID}"
            restart: always
            ports:
                - 1883:1883
    ```

### Start the container and add functionality to Node-RED

* Start the container with: 

  ```
  docker-compose -f docker-compose.devl.yml up -d
  ```

* Open `http://localhost:8200/` to start developing in Node-Red.