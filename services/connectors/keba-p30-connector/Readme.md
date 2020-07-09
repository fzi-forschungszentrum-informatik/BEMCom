# KEBA P30 Connector

This is a connector to integrate the [KEBA P30 charge station](https://www.keba.com/de/emobility/products/product-overview/produktubersicht).



### Supported Gateways

No gateway, the charge station communicated directly via Ethernet.



### Supported Devices

The connector should be able to process sensor datapoints of all existing Homematic devices. Currently only actuator datapoints of parameter type `SET_TEMPERATURE` are recognized automatically and exposed as available datapoints. The following devices have been tested 

| Manufacturer | Model                             | Tested?/Remarks? |
| ------------ | --------------------------------- | ---------------- |
| KEBA         | P30 charge station.               | Tested.          |



### Configuration

##### Ports

| Port                    | Usage/Remarks                                                |
| ----------------------- | ------------------------------------------------------------ |
| 1880                    | Node-RED development user interface.                         |
| 7090 | UDP Port used by the charge station to receive and send messages. The charge station insists on sending the messages back on exactly this port. |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| KEBA_P30_URL           | keba-p30.domain.de  | The DNS name or IP address of the charge station.            |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup.
* Optional: Update the image of the node-red-connector-template by editing [source/Dockerfile](source/Dockerfile) 
* Start the development instance with  `docker-compose up -d`
* Edit the flows, ensure everything works as expected.
* Export the changed flows and update/create the files in [./source/flows/](./source/flows/). The filenames should be the flows ids.
* Update the image tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 
* Run the new image and check once more everything works as expected.
* Document your changes and new tag by appending the list below.
* git add, commit and push.



### Changelog

| Tag   | Changes                      |
| ----- | ---------------------------- |
| 0.1.0 | Initial version              |