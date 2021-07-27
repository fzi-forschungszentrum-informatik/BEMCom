<font color="red">TODO: Check this, and merge documentation from final report, paper, and the API docs.</font>

# BEMCom Message Protocol

The BEMCom message protocol specifies how the services communicate within the application. A primary concern was to avoid restrictions on possible implementations of the services. Hence, the message protocol uses [MQTT](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html) to transport messages between the services, which was chosen as it is well established, robust, and open source implementations of clients exist for many platforms and programming languages (see e.g. [here](https://www.eclipse.org/paho/index.php)). While MQTT can be used to transport arbitrary strings, it is relatively common to encode the MQTT payload as [JSON](https://www.ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf) objects. The BEMCom message protocol follows this approach, as JSON objects are easy to interpret for humans, and JSON parsers should be available for any relevant programming language.

The BEMCom Message Protocol consists primarily of six core message types which are used in every BEMCom application. Additionally two additional message types exist which allow the usage of controller services. For each message type a description is provided, followed by the MQTT topic on which the message type should be published. Furthermore, the general format of the messages is defined, i.e. the fields that are expected in the JSON string, including an explanation how the field value should be interpreted. Finally, an example message per corresponding message type is provided.



## Core Messages

The following six message types are required for every BEMCom application.

### Log Message

A message type emitted by a connector service to forward a log message that was written while running the connector. It is consumed by the API service and brought to display for the administrator to occasionally inspect the operation of the connector.

#### Topic:

```
<Connector_name>/logs
```

Here, `<Connector_name>` should be replaced with the name of the connector as configured in the API service.

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
<Connector_name>/heartbeat
```

Here, `<Connector_name>` should be replaced with the name of the connector as configured in the API service.

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
<Connector_name>/available_datapoints
```

Here, `<Connector_name>` should be replaced with the name of the connector as configured in the API service.

#### Format:

```
{
    "sensor": {
        <string>: <string>,
        <string>: <string>,
        ...
    },
    "actuator": {
        <string>: <string>,
        <string>: <string>,
        ...
    }
}
```

#### Fields:

| Key                           | Value description                                            |
| ----------------------------- | ------------------------------------------------------------ |
| `"sensor"`                    | An object containing one entry for every available sensor datapoint. If no datapoints are known it must be an empty object. The entry should be formated as `{internal_dp_id}: {example_value}` , where `{internal_dp_id}` is some arbitrary but unique string that the connector defines and uses to identify a particular datapoint. `{example_value}` is an arbitrarily chosen value that the datapoint had at one time. It should be refrained from sending available datapoint message if only `{example_value}` has been changed, to prevent flooding the API service. |
| `"next_heartbeats_timestamp"` | Similar to `"sensor"` but for actuator datapoints respectively. |



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



























### Heartbeat

#### Topic:

```
<Connector_name>/heartbeat
```

##### Format:

```
"payload": {
	"this_heartbeats_timestamp": <unix timestamp in ms>,
	"next_heartbeats_timestamp": <unix timestamp in ms>,
}
```

### Example:

```
"payload": {
	"this_heartbeats_timestamp": 1571927361261,
	"next_heartbeats_timestamp": 1571927366261,
}
```

# Available Datapoints (from Connector)

### Requirements on Connector

* Must publish a list of available datapoints 
* Connector can do so in an iterative fashion, e.g. by just listening to the stream of incoming messages and send an update for every message that contains a new datapoint.
* The connector should only remove a datapoint (that has been send to the admin panel before) from the list if the datapoint is not available any more, b/c that is what the admin panel will assume happend.

#### Topic:

```
<Connector_name>/available_datapoints
```

### Format:

Example values can be set to empty strings if no examples are provided.

```
"payload": {
	"sensor": {
		<internal id of sensor 1>: <example value of sensor 1>,
        <internal id of sensor 2>: <example value of sensor 2>,
        ...
	},
	"actuator": {
		<internal id of actuator 1>: <example value of actuator 1>,
		<internal id of actuator 2>: <example value of actuator 2>,
		...
	}
}
```

### Example:

```
"payload": {
	"sensor": {
		"Channel__P__value__0": 0.122,
        "Channel__P__unit__0": "kW",
	},
	"actuator": {
		"Channel__P__setpoint__0": 0.4,
	}
}
```

Internal ID could also be something like:

```
soap:Envelope__soap:Body__0__getMeterResponse__0__getMeterResult:__0__channel__0__Channel__0__P__0__value__0
```



# Datapoint Map (to Connector)

#### Topic:

```
<Connector_name>/datapoint_map
```

### Format:

```
"payload": {
	"sensor": {
		<internal id of sensor 1>: <mqtt topic of sensor 1>,
		<internal id of sensor 2>: <mqtt topic of sensor 2>,
        ...
	},
	"actuator": {
		<mqtt topic of actuator 1>: <internal id of actuator 1>,
		<mqtt topic of actuator 2>: <internal id of actuator 2>,
		...
	}
}
```

### Example:

```
"payload": {
	"sensor": {
		"Channel__P__value__0": "example-connector/msgs/0001",
        "Channel__P__unit__0": "example-connector/msgs/0002",
	},
	"actuator": {
		"example-connector/msgs/0003": "Channel__P__setpoint__0",
	}
}
```

# Datapoint Value (from/to Connector)

### Topic:

```
<Connector_name>/messages/<datapoint_id>/value
```

### Format:

```
"payload": {
	"value": <numeric/text value>,
	"timestamp": <unix timestamp in ms>,
}
```

### Example:

```
"payload": {
	"value": 16.68,
	"timestamp": 1564489613491,
}

"payload": {
	"value": "ON",
	"timestamp": 1564489613491,
}
```

# Datapoint Schedule (to Controller)

A schedule created by the optimizer. The controller will execute the schedule, i.e. forward the values to the connectors at the specified time, as long as the corresponding sensor value is within the range defined by the setpoint. 

Conventions for timestamps and values.

* `timestamp`: Timestamp at which the Schedule message has been received by the API (will be set automatically)
* `from_timestamp`: Timestamp at which the value should take effect. `null` refers to immediately.
* `to_timestamp`: Timestamp at which the value should take no longer effect. If the schedule contains no following entry in schedule the datapoint value is set to  `null`.  A value of `null`  means that the the value should be set forever (i.e. until it is overwritten by a new schedule).
* `value`: The value that will be sent to the actuator datapoint. Must be within the min, max or acceptable values of the actuator datapoint. A value of `null` refers to no setpoint for datapoint, in most cases that means that a function is set to off, e.g. an AC temperature setpoint set to null will switch of the AC.

### Topic:

```
<Connector_name>/messages/<datapoint_id>/schedule
```

### Format:

```
"payload": {
	"schedule": [
		{
			"from_timestamp": <unix timestamp in ms or null.>,
			"to_timestamp": <unix timestamp in ms or null.>,
			"value": <numeric/text value or null>,
		},
		{
			"from_timestamp": <unix timestamp in ms or null.>,
			"to_timestamp": <unix timestamp in ms or null.>,
			"value": <numeric/text value or null>,
		},
		...
	]
	"timestamp": <unix timestamp in ms>,
}
```

### Example:

Will set an actuator to the value 21 from the time the message is received by the controller until time 1564489613491 after which the actuator is set to off.

```
{
    "schedule": [
        {
            "from_timestamp": null,
            "to_timestamp": 1564489613491,
            "value": 21
        },
        {
            "from_timestamp": 1564489613491,
            "to_timestamp": null,
            "value": null
        }
    ],
    "timestamp": 1564489613491
}
```

# Datapoint Setpoint (to Controller)

A setpoint, most likely generated by user interaction, defines the acceptable range/values for the controlled value within a control group.

**fix/complete below**

Conventions for timestamps for Datapoint Schedule apply, additionally: 

* `min_value`: Minimum value the controlled datapoint should have (applicable for continuous datapoints).  `null` refers to no restriction.
* `max_value`: Maximum value the controlled datapoint should have (applicable for continuous datapoints). `null` refers to no restriction.
* `accpetable_values`: List of acceptable values the controlled datapoint should have (applicable for discrete datapoints). `null` refers to no restriction.

### Topic:

```
<Connector_name>/messages/<datapoint_id>/schedule
```

### Format:

```
"payload": {
	"setpoint": [
		{
			"from_timestamp": <unix timestamp in ms or null.>,
			"to_timestamp": <unix timestamp in ms or null.>,
			"min_value": <numeric value or null>,
			"max_value": <numeric value or null>,
			"preferred_value": <numeric/text value>,
			"acceptable_values": null or [
				<numeric/text value>,
				<numeric/text value>,
				....
			]
		},
		{
			"from_timestamp": <unix timestamp in ms or null.>,
			"to_timestamp": <unix timestamp in ms or null.>,
			"min_value": <numeric value or null>,
			"max_value": <numeric value or null>,
			"preferred_value": <numeric/text value>,
			"acceptable_values": null or [
				<numeric/text value>,
				<numeric/text value>,
				....
			]
		},
		...
	]
	"timestamp": <unix timestamp in ms>,
}
```

### Example:

Will set an actuator to the value 21 from the time the message is received by the controller until time 1564489613491 after which the actuator is set to off.

```
"payload": {
		{
			"from_timestamp": null,
			"to_timestamp": 1564489613491,
			"value": 21,
		},
		{
			"from_timestamp": 1564489613491,
			"to_timestamp": null,
			"value": null,
		},
}
```

# 







# Raw Message (from Connector)



# Restore Raw Message (to Database)