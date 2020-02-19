 Format of messages between connectors and the API.

<span style="color:red;font-weight:bold">Connect connectors and Raw Message logging over MQTT too?</span>

# Log messages (from Connector)

### Topic:

```
<Connector_name>/logs
```

### Format:

The emitter field allows the identification of the logging node in Node-RED, which speeds up failure diagnostics in large flows. Can be left blanc for other connectors.

```
"payload": {
	"timestamp": <unix timestamp in ms>,
	"msg": <the log message text>,
	"emitter" <The node/process/function generating the log>
	"level" <Python log level as int>
}
```

### Example:

```
"payload": {
    "timestamp": 1571843907448,
    "msg": "TEest 112233",
    "emitter": "cd54c61d.3064d8",
    "level": 20,
}
```

# Heartbeat (from Connector)

### Topic:

```
<Connector_name>/heartbeat
```

### Format:

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

# Datapoint Message (from/to Connector)

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