# OCPP Connector

This is a connector to communicate with ocpp charging stations using the ocpp 1.6 protocol. The library used is provided by The Mobility House (https://github.com/mobilityhouse/ocpp).
The Open ChargePoint Protocol (OCPP) defines the central system (here BEMCom) as a server, while the ChargePoint acts as a client. This is different to many hardware communication protocols.  

# Implementation
Besides the classes ActuatorFlow, SensorFlow and Connector there is a class called ChargePoint that inherits from the corresponding class in the ocpp module
from The Mobility House. This class contains the protocoll-specific messages. OCPP uses websockets. The messages from the charge point are routed to the
corresponding method where the response to the charge point is defined. If there are values to be sent to the BEMCom message broker, a callback
method with the name "sensor_flow_handler" is executed. Messages passed to it will be made available in the BEMCom framework by using the method "run_sensor_flow" 
of the Connector class.
Once the connector starts, the synchronous DeviceDispatcher starts a sever using asyncio. Once the charging station connects to the server, the ChargePoint is
instantiated and the communication begins.

### Configuration
| OCPP_CONFIG | Usage/Remarks                           |
| ---- | --------------------------------------- |
| execute_send_charging_profile | No parameters, defines the actuator datapoint so that (constant) charging profiles can be sent. Interpreted as maximum power values in W. |
| execute_trigger_message       | No parameters, defines the actuator datapoint to trigger the chargepoint to send specific messages like meter values. |


##### Ports

| Port | Usage/Remarks                           |
| ---- | --------------------------------------- |
| 9000 | Port of the BEMCom Host (server), not the charge point. Has to be configured in the charge point als well if it is desired to use another one.|

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | ocpp-connector      | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| OCPP_CONFIG            | "execute_send_charging_profile"    | list of actuator datapoints. Have to begin with "execute_" |
| OCPP_PORT              | 9000                | Port of the Server (BEMCom host)                                            |
##### Volumes

None preferably. You should only add volumes, especially file mounts if it is really necessary. It introduces a lot of trouble with user id and file ownerships stuff.

##### Usage
Charging profiles consist of a single power value (in Watt) that remain active until the next value is sent. The messages sent from the chargepoint, like meter values, can be triggered
using the datapoint "execute_trigger_message". There, the following vales are allowed:

| Value in API    | Message                          |
| --------------- | -------------------------------- |
| 0               | "BootNotification"               |
| 1               | "DiagnosticsStatusNotification"  |
| 2               | "FirmwareStatusNotification"     |
| 3               | "Heartbeat"                      |
| 4               | "MeterValues"                    |
| 5               | "StatusNotification"             |


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
| 0.1.0 | First successful communication.            |
| 0.2.0 | First successfully sent charging profile   |
| 0.2.1 | Possible to trigger and receive meter values | 