# MQTT Connector

This is a connector to integrate data that is published on some MQTT broker (<u>not</u> the BEMCom app internal message broker.)

Sending values to actuator datapoints, i.e. to publish on the broker is currently not implemented.

<font color="red">TODO: Fix  issues here with push to raw message DB.</font>



### Supported Devices/Gateways

Any broker that implemented MQTT version 3.1.1 should work.



### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable              | Example  Value                          | Usage/Remarks                                                |
| -------------------------------- | --------------------------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME                   | brand-new-connector                     | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST                 | broker.domain.de                        | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST                 | 1883                                    | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB           | TRUE                                    | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                            | TRUE                                    | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| REMOTE_MQTT_BROKER_HOST          | broker.domain.de                        | The DNS name or IP address of the remote MQTT broker.        |
| REMOTE_MQTT_BROKER_PORT          | 1883                                    | The port of the remote MQTT broker.                          |
| REMOTE_MQTT_BROKER_USE_TLS       | FALSE                                   | If == "TRUE" (i.e. the string), will use TLS to encrypt the connection. |
| REMOTE_MQTT_BROKER_CA_FILE       | Wrap the multiline ca file with quotes. | A CA certificate (full chain) in pem format. If provided will use this CA certificate to verify that server certificate. |
| REMOTE_MQTT_BROKER_USERNAME      | john-doe                                | If not empty will try to login at the remote broker with this username. |
| REMOTE_MQTT_BROKER_PASSWORD      | very-secret                             | If not empty (and username not empty) will try to login at the remote broker with this password. |
| REMOTE_MQTT_BROKER_TOPIC_MAPPING | see below                               | A json string defining which topics should be forwarded to which datapoints. See Readme.md for details. |
| REMOTE_MQTT_BROKER_PARSE_JSON    | FALSE                                   | If == "TRUE" (i.e. the string), will try to parse the payload of the message received from the remote broker as JSON. Defaults to FALSE |



The content of REMOTE_MQTT_BROKER_TOPIC_MAPPING should be JSON string structured like this:

```json
{
    "sensor_topics": {
        "sensor/topic/1": {},
        "sensor/topic/with/single/+/wildcard": {},
        "sensor/topic/with/mulitlevel/wildcard/#": {}
    },
    "actuator_topics": {
        "actuator/topic/1": {
            "example_value": "22.0"
        }
    }
}
```

For `"sensor_topics"` just the topic strings (i.e. the keys) are relevant for now (this may change in future), wildcards are allowed. The example values are taken from the first message arriving per topic. The connector will try to parse any incoming payload as JSON. 

For `"actuator_topics"` the keys also specify the topics on which the value message should be published. Note that wildcards are not allowed for the actuator datapoints, as it would not be clear on which topic to publish in these cases.

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