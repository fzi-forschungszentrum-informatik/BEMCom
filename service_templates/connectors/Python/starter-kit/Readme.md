# Brand New Connector

This is a connector to integrate some sample devices



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
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. **Beware:** This is not the name of the image of the connector but of the created container. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |

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

* Update the version number (aka. the tag) in [source/connector/main.py](./source/connector/main.py) before building the docker image. 

* Execute [./build_docker_image.sh](./build_docker_image.sh) to build an updated image. 

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