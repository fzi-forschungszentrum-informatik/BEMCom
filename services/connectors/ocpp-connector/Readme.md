# Brand New Connector

This is a connector to communicate with ocpp charging stations using the ocpp 1.6 protocol. The library used is provided by The Mobility House (https://github.com/mobilityhouse/ocpp). An implementation using the same library has already been tested on the charging station, however the BEMcom implementation has not been fully tested yet. 

# Implementation
A class named ChargePoint that inherits from CP is created and overwritten and contains methods that interact with the charging station. The most important functions are on_boot_notification and execute_send_charging_profile. The class is instantiated in the connector class as cp.
To start the ocpp server, a new thread containing a new event loop is created in the connector initialization, and listens for incoming connections. Upon connection with the charging station, an infinite loop is created to listen to incoming messages, which are passed down to run_sensor_flow as raw_data. 
To parse the raw_data, we call cp.route_message to parse the message coming from the charging station using the mobilityhouse implementation.
Send_command receives datapoints parsed in the connector and executes the corresponding function from ChargePoint. 

P.S this implementation uses asyncio, so the behaviour may be different in the BEMcom framework.

The implementation has not been tested.



### Configuration

##### Ports

| Port | Usage/Remarks                           |
| ---- | --------------------------------------- |
| 9000 | OCPP port                               |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | ocpp-connector      | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| OCPP_PROFILE           | json                | This json contains the charging profile that has to be adjusted and sent to the station                        |
| OCPP_CONFIG            | json                | contains the commands to be executed e.g execute_send_charging_profile|
| OCPP_PORT                | 9000                | OCPP port                                                             |
##### Volumes

None preferably. You should only add volumes, especially file mounts if it is really necessary. It introduces a lot of trouble with user id and file ownerships stuff.



### Development Checklist

Follow the following steps while contributing to the connector:

* Update the `.env` file with suitable configuration for your local setup.

* Specify all required dependencies in [source/requirements.txt](source/requirements.txt).

* Optional: Install a local version of dependencies for local development:

  * ```bash
    # in service_templates/connectors/Python/
    pip install -e ./source/
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