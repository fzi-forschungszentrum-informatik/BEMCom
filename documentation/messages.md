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

<span style="color:red;font-weight:bold">Revise here if it does not make more sense to transfer the expected message format with placeholders.</span>

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
<Connector_name>/messages/<datapoint_id>
```

### Format:

Numeric Values:

```
"payload": {
	"value": <numeric value>,
	"timestamp": <unix timestamp in ms>,
}
```

Data/Strings: 

```
"payload": {
	"data": <data or string>,
	"timestamp": <unix timestamp in ms>,
}
```

### Format:

Numeric Values:

```
"payload": {
	"value": 16.68,
	"timestamp": 1564489613491,
}
```

Data/Strings: 

```
"payload": {
	"data": "ok",
	"timestamp": 1564489613491,
}
```

