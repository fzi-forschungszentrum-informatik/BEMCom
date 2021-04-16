# Fronius Solar API Connector

This is a connector that allows reading datapoint values from the Powerflow REST API of Fronius PV inverters.



### Supported Devices

Some remarks about the devices or just nothing.

| Manufacturer | Model      | Tested?/Remarks? |
| ------------ | ---------- | ---------------- |
| Fronius      | Symo GEN24 | Tested.          |



### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable    | Example  Value                                               | Usage/Remarks                                                |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector                                          | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de                                             | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                                                         | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                                                         | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                                                         | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| POLL_SECONDS           | 60                                                           | The period of polling the inverter.                          |
| INVERTER_POWERFLOW_URL | http://192.168.0.44:80/solar_api/v1/GetPowerFlowRealtimeData.fcgi | The URL of the Powerflow API, including IP address (or DNS name), port and HTTP path. |

##### Volumes

None.



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

| Tag   | Changes                                          |
| ----- | ------------------------------------------------ |
| 0.1.0 | First productive version.                        |
| 0.2.0 | Clean up environment variables and improve docs. |