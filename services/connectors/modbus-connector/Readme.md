# Modbus TCP Connector

This is a connector to communicate with Devices over ModbusTCP

##### Local Development:

* Install pyconnector template package `pip install -e` .
* Install requirements 

### Supported Gateways

Some remarks about the gateways or just nothing.

| Manufacturer  | Model                | Tested?/Remarks? |
| ------------- | -------------------- | ---------------- |
| Hardware Inc. | Precise gateway name | Tested.          |



### Supported Devices

Some remarks about the devices or just nothing.

| Manufacturer  | Model               | Tested?/Remarks? |
| ------------- | ------------------- | ---------------- |
| Hardware Inc. | Precise device name | Tested.          |



### Configuration

##### Ports

| Port | Usage/Remarks                           |
| ---- | --------------------------------------- |
| 1234 | Some port for incoming callbacks maybe? |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| MODBUS_MASTER_IP       | 192.168.0.1         | The ip adress or DNS name of the Modbus master device which we want to connect to. |
| MODBUS_MASTER_PORT     | 502                 | The port on which  the master device awaits Modbus communication. |

##### Volumes

None preferably. You should only add volumes, especially file mounts if it is really necessary. It introduces a lot of trouble with user id and file ownerships stuff.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup.
* Optional: Update the image of the python-connector-template by editing [source/Dockerfile](source/Dockerfile), e.g. to install dependencies.
* Start the development instance with  `docker-compose up`
* Place your code under [source/connector](./source/connector) but keep the [source/connector/main.py](./source/connector/main.py) as entrypoint. Ensure everything works as expected.
* Update the image name and tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 
* Run the new image and check once more everything works as expected.
* Document your changes and new tag by appending the list below.
* git add, commit and push.



### Changelog

| Tag   | Changes                                    |
| ----- | ------------------------------------------ |
| 0.0.1 | Some work in progress development version. |
| 0.1.0 | First productive version.                  |