# Senertec Dachs Connector

This is a connector to integrate the Senertec Dach combined heat and power plant. It uses the REST interface of the Dachs for communication.



### Supported Devices

| Manufacturer | Model     | Tested?/Remarks? |
| ------------ | --------- | ---------------- |
| Senertec     | Dachs 5.5 | Tested.          |



### Configuration

##### Ports

| Port | Usage/Remarks                        |
| ---- | ------------------------------------ |
| 1880 | Node-RED development user interface. |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| POLL_SECONDS           | 30                  | Wait time in seconds between polling the CHP for sensor data. |
| DACHS_IP               | dachs.example.com   | IP address or DNS name of the Dachs CHP that  should be communicated with. We expect the REST API exposed on port 8080 of that address. |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup.

* Optional: Update the image of the node-red-connector-template by editing [source/Dockerfile](source/Dockerfile) 

* Start the development instance with  `docker-compose up -d`

* Edit the flows, ensure everything works as expected.

* Export the changed flows and update/create the files in [./source/flows/](./source/flows/). The filenames should be the flows ids.

* If you have added functionality that needs usernames and passwords, you also need to export the flow_cred.json file from the container, as the credentials are not exported with the flows. You might do this with something like:

  ```bash
  # Execute this in the root directory of the connector.
  CONTAINER_NAME=$(cat docker-compose.yml | grep container_name | cut -d : -f 2 | xargs )
  docker cp $CONTAINER_NAME:/data/flows_cred.json ./source/
  ```

  **Please note:** 
  The credentials are stored unencrypted. If the connector needs credentials that are not well known (e.g. provided in the user manual of the device), it is better set them at runtime via [environment variable](https://nodered.org/docs/user-guide/environment-variables). This way the credentials will never appear in the repository and can be set by each user to the required values.

* Update the image tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 

* Run the new image and check once more everything works as expected.

* Document your changes and new tag by appending the list below.

* git add, commit and push.



### Changelog

| Tag   | Changes                                  |
| ----- | ---------------------------------------- |
| 0.1.0 | First productive version. Read only yet. |