# KNX Connector

This is a connector to integrate KNX devices.



### Supported Gateways

Note that currently only KNX IP gateways are supported that allow a TCP tunnel connection.

| Manufacturer | Model                                                        | Tested?/Remarks? |
| ------------ | ------------------------------------------------------------ | ---------------- |
| JUNG         | [KNX Spannungsversorgung 320 mA mit IP-Schnittstelle](https://www.jung.de/at/online-katalog/1009783303/) | Tested.          |



### Supported Devices

Any KNX device should work in theory. It might happen that some [KNX datapoint types](https://www.knx.org/wAssets/docs/downloads/Certification/Interworking-Datapoint-types/03_07_02-Datapoint-Types-v02.02.01-AS.pdf) are not supported yet. Check the definition of `transcoder_by_dpt_number` in [transcoder.py](source/connector/transcoder.py).



### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. **Beware:** This is not the name of the image of the connector but of the created container. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| KNX_GATEWAY_HOST       | knx_gw.example.com  | The DNS name or IP address of the KNX gateway to connect to. |
| KNX_GATEWAY_PORT       | 3672                | The corresponding port for the gateway. Defaults to `3671`   |
| KNX_DATAPOINTS         | see below           | see below                                                    |

`KNX_DATAPOINTS` is a JSON object mapping from KNX group addresses to KNX datapoint types. It is necessary to tell the connector how to interpret the raw bytes received from the KNX bus.

The `KNX_DATAPOINTS` object must contain a `sensors` and `actuators` entry and could look like follows:

```json
{
    "sensor": {
        "2/3/111": "DPST-3-7",
        "2/3/112": "DPST-5-1",
        "2/3/113": "DPST-1-1"
    },
    "actuator": {
        "2/3/113": "DPST-1-1"
    }
}
```

You may want to create the mapping from group address to datapoint type from an ETS CSV export with the following lines:

```python
import json
import pandas as pd

knx_datapoints = pd.read_csv(file_name, sep="\t", encoding="latin-1")
json.dumps({r.Address: r.DatapointType for _, r in knx_datapoints.iterrows()}, indent=4)
```

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

| Tag   | Changes                   |
| ----- | ------------------------- |
| 0.1.0 | First productive version. |