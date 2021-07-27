# BEMCom Message Protocol

The BEMCom message protocol specifies how the services communicate within the application. A primary concern was to avoid restrictions on possible implementations of the services. Hence, the message protocol uses [MQTT](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html) to transport messages between the services, which was chosen as it is well established, robust, and open source implementations of clients exist for many platforms and programming languages (see e.g. [here](https://www.eclipse.org/paho/index.php)). While MQTT can be used to transport arbitrary strings, it is relatively common to encode the MQTT payload as [JSON](https://www.ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf) objects. The BEMCom message protocol follows this approach, as JSON objects are easy to interpret for humans, and JSON parsers should be available for any relevant programming language.

The BEMCom Message Protocol consists primarily of six core message types which are used in every BEMCom application. Additionally two additional message types exist which allow the usage of controller services. For each message type a description is provided, followed by the MQTT topic on which the message type should be published. Furthermore, the general format of the messages is defined, i.e. the fields that are expected in the JSON string, including an explanation how the field value should be interpreted. Finally, an example message per corresponding message type is provided.



## Core Message Types

The following six message types are required for every BEMCom application.



### Log Message

A message type emitted by a connector service to forward a log message that was written while running the connector. It is consumed by the API service and brought to display for the administrator to occasionally inspect the operation of the connector.

#### Topic:

```
${Connector_name}/logs
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
	"timestamp": <integer>,
	"msg": <string>,
	"emitter" <string or null>,
	"level" <integer>
}
```

#### Fields:

| Key           | Value description                                            |
| ------------- | ------------------------------------------------------------ |
| `"timestamp"` | The time the message was logged by the connector as timestamp in milliseconds since 1970-01-01 UTC. |
| `"msg"`       | The text of the log message.                                 |
| `"emitter"`   | A string that supports the identification of the emitting entity, e.g. a function name. Can be `null` if not provided. |
| `"level"`     | The severity level (i.e. log level) of the message as integer following the [python log level convention](https://docs.python.org/3/library/logging.html#logging-levels). |

#### Example:

```json
{
    "timestamp": 1571843907448,
    "msg": "Connector running fine.",
    "emitter": "main",
    "level": 20
}
```



### Heartbeat

A message type emitted by a connector service to indicate that it is running as expected. Is is consumed by the API service and brought to display for the administrator to occasionally verify that the connector operates as intended.

#### Topic:

```
${Connector_name}/heartbeat
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
    "this_heartbeats_timestamp": <integer>,
    "next_heartbeats_timestamp": <integer>
}
```

#### Fields:

| Key                           | Value description                                            |
| ----------------------------- | ------------------------------------------------------------ |
| `"this_heartbeats_timestamp"` | The time the heartbeat message was created by the connector as timestamp in milliseconds since 1970-01-01 UTC. |
| `"next_heartbeats_timestamp"` | The time the connector will create the following heartbeat message in milliseconds since 1970-01-01 UTC. |

#### Example:

```json
{
    "this_heartbeats_timestamp": 1571927361261,
    "next_heartbeats_timestamp": 1571927366261
}
```



### Available Datapoints

A message type emitted by a connector that contains all datapoints provided by the devices connected to the connector. Connectors may build up the list of available datapoints in an iterative fashion, e.g. by listening to the incoming data of the devices. The message thus represents the currently best knowledge of the connector. Once new datapoints have been identified, an updated message with available datapoints must be published. The message is used by the API service to present all available datapoints to the administrator. Based on the available datapoints, the administrator selects a set of datapoints which should be processed by the connector service.

#### Topic:

```
${Connector_name}/available_datapoints
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
    "sensor": {
        <string>: <string>
    },
    "actuator": {
        <string>: <string>
    }
}
```

#### Fields:

| Key          | Value description                                            |
| ------------ | ------------------------------------------------------------ |
| `"sensor"`   | An object containing one entry for every available sensor datapoint. If no datapoints are known it must be an empty object. The entry should be formated as `${internal_dp_id}: ${example_value}` , where `${internal_dp_id}` is some arbitrary but unique string that the connector defines and uses to identify a particular datapoint. `${example_value}` is an arbitrarily chosen value that the datapoint had at one time. It should be refrained from sending available datapoint message if only `${example_value}` has been changed, to prevent flooding the API service. |
| `"actuator"` | Similar to `"sensor"` but for actuator datapoints respectively. |

#### Example:

```json
{
    "sensor": {
        "Channel__P__value__0": "0.122",
        "Channel__P__unit__0": "kW"
    },
    "actuator": {
        "Channel__P__setpoint__0": "0.4"
    }
}
```



### Datapoint Map

A message type emitted by the API service to tell a connector which datapoints should be processed, i.e. for which datapoints the value should be sent to the message broker. Also defines a unique topic for every selected datapoint.

#### Topic:

```
${Connector_name}/datapoint_map
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
    "sensor": {
        <string>: <string>
    },
    "actuator": {
        <string>: <string>
    }
}
```

#### Fields:

| Key          | Value description                                            |
| ------------ | ------------------------------------------------------------ |
| `"sensor"`   | An object containing one entry for every selected sensor datapoint. Must be an empty object if no datapoints are selected at all. The entry should be formated as `${internal_dp_id}: ${mqtt_topic}`, where  `${internal_dp_id}` must match an id listed in the most recent available datapoints message by the same connector service. The `${mqtt_topic}`  is used by the connector service to publish values of the selected datapoint as datapoint value message type. |
| `"actuator"` | An object containing one entry for every selected actuator datapoint. Must be an empty object if no datapoints are selected at all. The entry should be formated as `${mqtt_topic}: $​{internal_dp_id}`, where `${internal_dp_id}` must match an id listed in the most recent available datapoints message by the same connector service. The `$​​{mqtt_topic}` is used by the connector service to subscribe to the topic of the datapoint, incoming datapoint value messages on the topic will be processed and and the value is forwarded to the respective device. |

#### Example:

```json
{
    "sensor": {
        "Channel__P__value__0": "example-connector/messages/1/value",
        "Channel__P__unit__0": "example-connector/messages/2/value"
    },
    "actuator": {
        "example-connector/messages/3/value": "Channel__P__setpoint__0"
    }
}
```



### Raw Message

A message type emitted by a connector service to indicate that it is running as expected. Is is consumed by the API service and brought to display for the administrator to occasionally verify that the connector operates as intended.

#### Topic:

```
${Connector_name}/raw_message_to_db
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
    "raw_message": <string>,
    "timestamp": <integer>
}
```

#### Fields:

| Key             | Value description                                            |
| --------------- | ------------------------------------------------------------ |
| `"raw_message"` | The raw message received from a device, without any modifications (if possible), represented as a string. |
| `"timestamp"`   | The time the connector received the raw message in milliseconds since 1970-01-01 UTC. |

#### Example:

```json
{
    "raw_message": "device_1:{sensor_1:2.12}",
    "timestamp": 1573680749000
}
```



### Datapoint Value

For a sensor datapoint: Represents a measurement emitted by a device. Message is published by the corresponding connector service. For an actuator datapoint:  Represents a set value that should be "written" to a device actuator. Message is created by an external entity, sent to the API service which publishes the message on the broker.

#### Topic:

```
${Connector_name}/messages/${datapoint_id}/value
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service. `$​{datapoint_id}` is an identifier that the API service has assigned to the respective datapoint by defining the topic with the latest datapoint map message.

#### Format:

```
{
    "value": <string>,
    "timestamp": <integer>
}
```

#### Fields:

| Key           | Value description                                            |
| ------------- | ------------------------------------------------------------ |
| `"value"`     | The last value of the datapoint. Will be a string or `null`. Values of numeric datapoints are sent as strings too, as this drastically reduces the effort for implementing the external (REST) interface of the API service. |
| `"timestamp"` | For sensor datapoints: The time the value was received by the connector. <br />For actuator datapoints: The time the message was created by the external entity. <br />Both in milliseconds since 1970-01-01 UTC. |

#### Example:

```json
{
    "value": "18.0",
    "timestamp": 1585858832910
}
```



## Extended Message Types for Controllers

The following message types are optional and are only relevant for BEMCom applications that employ controller services. The message types are implemented in the [Django API service](../services/apis/django-api/) and [all Controller services](../services/controllers/) provided in this repository. 



### Datapoint Setpoint

A message type emitted by the API service to the controller. The setpoint specifies the demand of the users of the system. The setpoint must hold a preferred_value which is the value the user would appreciate most, and can additionally define flexibility of values the user would also accept. The setpoint message is used by optimization algorithms as constraints while computing schedules, as well as by controller services to ensure that the demand of the user is always met.

#### Topic:

```
${Connector_name}/messages/${datapoint_id}/setpoint
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service. `${datapoint_id}` is an identifier that the API service has assigned to the respective datapoint by defining the topic with the latest datapoint map message.

#### Format:

```
{
	"setpoint": [
		{
			"from_timestamp": <integer or null>,
			"to_timestamp": <integer or null>,
			"preferred_value": <string or null>,
			"acceptable_values": [
				<string>
			],
			"min_value": <float or null>,
			"max_value": <float or null>
		}
	],
	"timestamp": <integer>
}
```

#### Fields:

| Key                   | Value description                                            |
| --------------------- | ------------------------------------------------------------ |
| `"setpoint"`          | A JSON array holding zero or more datapoint setpoint items. Can also be set to `null`. |
| `"from_timestamp"`    | The time in milliseconds since 1970-01-01 UTC that the setpoint itme should be applied. Can be `null` in which case the item should be applied immediately after the setpoint is received by the controller. |
| `"to_timestamp"`      | The time in milliseconds since 1970-01-01 UTC that the setpoint item should no longer be applied. Can be `null` in which case the item should be applied forever, or more realistically, until a new setpoint is received. |
| `"preferred_value"`   | Specifies the preferred setpoint of the user. This value should be send to the actuator datapoint by the controller if either no schedule is applicable, or the current value of the corresponding sensor datapoint is out of range of `acceptable_values` (for discrete datapoints) or not between `min_value` and `max_value` (for continuous datapoints) as defined in this setpoint item. Furthermore, the value of `preferred_value` must match the requirements of the actuator datapoint, i.e. it must be in `acceptable_values` (for discrete datapoints) or between `min_value` and `max_value` (for continuous datapoints) as specified in the corresponding fields of the actuator datapoint. Can be `null`. |
| `"acceptable_values"` | Specifies the flexibility of the user regarding the sensor datapoint for discrete values. That is, it specifies the actually realized values the user is willing to accept. Consider e.g. the scenario where a room with a discrete heating control has currently 16°C. If the user specified this field with [20, 21, 22] it means that only these three temperature values are acceptable. This situation would cause the controller to immediately send the preferred_value to the actuator datapoint, even if the schedule would define a value that lays within the acceptable range. Can be an empty array or `null` to to indicate that there is no flexibility, the controller will always execute the `preferred_value` and ignore the schedule. |
| `"min_value"`         | Similar to `acceptable_values` above but defines the minimum valuethe user is willing to accept for continuous datapoints. Can be `null` to indicate that no minimum exists. The controller will ignore the schedule and execute `preferred_value` if the controlled datapoint value is below `min_value`. |
| `"max_value"`         | Similar to `acceptable_values` above but defines the maximum valuethe user is willing to accept for continuous datapoints. Can be `null` to indicate that no maximum exists. The controller will ignore the schedule and execute `preferred_value` if the controlled datapoint value is above `max_value`. |
| `"timestamp"`         | The time the message was created by the external entity in milliseconds since 1970-01-01 UTC. |

#### Example:

Here a setpoint that could belong to the set temperature of an AC, which only accepts discrete temperatures. The message indicates that setpoint should be applied immediately and should last until Tuesday, 30. July 2019 12:26:53. The user would prefer a temperature of 19°C, but would also accept 17, 18, 20 and 21°C set temperatures.

```
{
    "setpoint": [
        {
            "from_timestamp": null,
            "to_timestamp": 1564489613491,
            "preferred_value": "19",
            "acceptable_values": [
                "17",
                "18",
                "19",
                "20",
                "21"
            ]
        }
    ],
    "timestamp": 1586301356394
}
```



### Datapoint Schedule

A message type emitted by the API service to the controller. The schedule is a list of actuator values computed by an optimization algorithm that should be executed on the specified actuator datapoint as long as the setpoint constraints are not violated.

#### Topic:

```
${Connector_name}/messages/${datapoint_id}/schedule
```

Here, `${Connector_name}` should be replaced with the name of the connector as configured in the API service. `${datapoint_id}` is an identifier that the API service has assigned to the respective datapoint by defining the topic with the latest datapoint map message.

#### Format:

```
{
	"setpoint": [
		{
			"from_timestamp": <integer or null>,
			"to_timestamp": <integer or null>,
			"value": <string or null>,
		}
	],
	"timestamp": <integer>
}
```

#### Fields:

| Key                | Value description                                            |
| ------------------ | ------------------------------------------------------------ |
| `"setpoint"`       | A JSON array holding zero or more datapoint schedule items. Can also be set to `null`. |
| `"from_timestamp"` | The time in milliseconds since 1970-01-01 UTC that the value should be applied. Can be `null` in which case the value should be applied immediately after the schedule is received by the controller. |
| `"to_timestamp"`   | The time in milliseconds since 1970-01-01 UTC that the value should no longer be applied. Can be `null` in which case the value should be applied forever, or more realistically, until a new schedule is received. |
| `"value"`          | The value that should be sent to the actuator datapoint. The value must be larger or equal min_value (as listed in the datapoint metadata) if the datapoints data format is continuous_numeric. The value must be smaller or equal max_value (as listed in the datapoint metadata) if the datapoints data format is continuous_numeric. The value must be in the list of acceptable_values (as listed in the datapoint metadata) if the datapoints data format is discrete. Can be `null`. |
| `"timestamp"`      | The time the message was created by the external entity in milliseconds since 1970-01-01 UTC. |

#### Example:

Here a schedule that could request a setpoint of 19.0 °C for an AC, starting immediately, and lasting until  Tuesday, 30. July 2019 12:26:53. After that time it would request the AC to be switched off. The interpretation of the null for value depends on the datapoint and should be explicitly mentioned in the datapoint description field. 

```
{
    "schedule": [
        {
            "from_timestamp": null,
            "to_timestamp": 1564489613000,
            "value": "19.0"
        },
        {
            "from_timestamp": 1564489613000,
            "to_timestamp": null,
            "value": null
        }
    ],
    "timestamp": 1586290918529
}
```



### Controlled Datapoints

A message type emitted by the API service to tell a controller which datapoints should be controlled by the service. The important information is thereby the mapping between sensor and actuator datapoints and the corresponding MQTT addresses.

#### Topic:

```
${Controller_name}/controlled_datapoints
```

Here, `${Controller_name}` should be replaced with the name of the <u>controller</u> as configured in the API service.

#### Format:

```
[
    {
        "sensor": {
            "value": <string>
        },
        "actuator": {
            "value": <string>,
            "setpoint": <string>,
            "schedule": <string>,

        },
    }
]
```

#### Fields:

See also the definition of the datapoint value, datapoint setpoint and datapoint schedule messages for further explanations.

| Key          | Value description                                            |
| ------------ | ------------------------------------------------------------ |
| `"sensor"`   | Specifies the MQTT topic on which the datapoint value message for the sensor datapoint are published by the connector. |
| `"actuator"` | Specifies the MQTT topics for the actuator datapoint. That is, the topics on which setpoint and schedule messages will be published by the API service, but also the topic on which the controller will publish value messages for the corresponding connector to receive. |

#### Example:

```json
[
    {
        "sensor": {
            "value": "example-connector/messages/7/value"
        },
        "actuator": {
            "value": "example-connector/messages/2/value",
            "setpoint": "example-connector/messages/2/setpoint",
            "schedule": "example-connector/messages/2/schedule"
        }
    },
    {
        "sensor": {
            "value": "example-connector/messages/12/value"
        },
        "actuator": {
            "value": "example-connector/messages/5/value",
            "setpoint": "example-connector/messages/5/setpoint",
            "schedule": "example-connector/messages/5/schedule"
        }
    }
]
```

