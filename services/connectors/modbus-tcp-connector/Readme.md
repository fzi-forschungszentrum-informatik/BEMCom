# Modbus TCP Connector

This is a connector to communicate with Devices over ModbusTCP. A short introduction to Modbus can e.g. be found [here](https://www.csimn.com/CSI_pages/Modbus101.html).

The following Modbus function codes are currently supported:

| Modbus Function Code | Name                  |
| -------------------- | --------------------- |
| 3                    | Read holding register |
| 4                    | Read input register   |

The following Modbus function codes are planned for future support:

| Modbus Function Code | Name                             |
| -------------------- | -------------------------------- |
| 1                    | Read coil                        |
| 2                    | Read discrete input              |
| 5                    | Write single coil                |
| 6                    | Write single holding register    |
| 15                   | Write multiple coils             |
| 16                   | Write multiple holding registers |



### Supported Devices/Gateways

This connector should be able to communicate with any Modbus Device or Gateway. The following devices have been explicitly tested:

| Manufacturer | Model      | Tested?/Remarks? |
| ------------ | ---------- | ---------------- |
| Janitza      | UMG-96RM-E | Tested.          |



### Configuration

##### Environment Variables

| Enironment Variable    | Example  Value                   | Usage/Remarks                                                |
| ---------------------- | -------------------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | modbus-tcp-connector-device-name | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de                 | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                             | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                             | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                             | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| POLL_SECONDS           | 30                               | The period of polling the Modbus device/gateway for sensor data. |
| MODBUS_MASTER_IP       | 192.168.0.1                      | The ip adress or DNS name of the Modbus master device which we want to connect to. |
| MODBUS_MASTER_PORT     | 502                              | The port on which  the master device awaits Modbus communication. |
| MODBUS_CONFIG          |                                  | TODO                                                         |
| MODBUS_POLL_SECONDS    |                                  | TODO                                                         |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Update the `.env` file with suitable configuration for your local setup.

* Specify all required dependencies in [source/requirements.txt](source/requirements.txt).

* Optional: Install a local version of dependencies for local development:

  * ```bash
    # in service_templates/connectors/Python/
    pip install ./source/
    ```

  * ```bash
    # in the folder of your connector
    pip install -r ./source/requirements.txt
    ```

* Place your code under [source/connector](./source/connector) but keep the [source/connector/main.py](./source/connector/main.py) as entrypoint. Place your tests in [source/connector/tests](./source/connector/tests).

* Ensure all relevant tests exist and all of those are passed before preceding. 

* Update the image name and tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 

  ```bash
  # This will fail if not all tests are passed.
  bash build_docker_image.sh
  ```

* Document your changes and new tag by appending the list below.

* git add, commit and push.



### Changelog

| Tag   | Changes                                    |
| ----- | ------------------------------------------ |
| 0.0.1 | Some work in progress development version. |
| 0.1.0 | First productive version.                  |