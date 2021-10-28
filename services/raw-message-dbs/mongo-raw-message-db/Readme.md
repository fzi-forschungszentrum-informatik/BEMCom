# Mongo Raw Message DB

This is a MongoDB based Raw Message DB for BEMCom. 



### Configuration

##### Ports

| Port  | Usage/Remarks                                                |
| ----- | ------------------------------------------------------------ |
| 27017 | Port to directly connect to MongoDB. Opening this port is not necessary for storing raw messages by connectors, only for access with external tools. You should definitely configure the passwords before opening this port. |

##### Environment Variables

| Enironment Variable         | Example  Value      | Usage/Remarks                                                |
| --------------------------- | ------------------- | ------------------------------------------------------------ |
| MQTT_BROKER_HOST            | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_PORT            | 1883                | The port of the MQTT broker.                                 |
| MONGO_INITDB_ROOT_USERNAME  | mongo-admin         | If set, will automatically create an admin account on the very first startup. See [here (Section Environment Variables)](https://hub.docker.com/_/mongo) for details. |
| MONGO_INITDB_ROOT_PASSWORD  | very!secret&        | See above.                                                   |
| MONGO_USERNAME              | mongo-user          | Starts the MongoDB with [access control](https://docs.mongodb.com/manual/tutorial/enable-authentication/) if not left blank.<br />If not blank is used as the username of the account that is used by the mqtt-integration.py script to connect to the MongoDB. |
| MONGO_PASSWORD              | very!secret&        | The password of the account that is used by the mqtt-integration.py script to connect to the MongoDB. |
| MONGO_LOGIN_DB              | admin               | The Login DB of the account that is used by the mqtt-integration.py script to connect to the MongoDB. Should be set to `admin` unless you have changed it manually. |
| MQTT_TOPIC_ALL_RAW_MESSAGES | +/raw_message_to_db | The topic on the broker on which the raw messages will be published. Stick to the convention of the example value given here to prevent messy surprises. |
| MQTT_INTEGRATION_LOG_LEVEL  | INFO                | The level of log messages that will be logged to stdout of the container for the mqtt-integration.py script. Can be any of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `Critical`. The Info is reasonable for normal operation. |


##### Volumes

| Path in Container | Usage/Remarks                                                |
| ----------------- | ------------------------------------------------------------ |
| /data/db          | Folder in which MongoDB stores its DB. Is required to persist the Database. The folder on the host machine must exist before the container is run for the first time and the container must be started with the user id of the user who own the folder on the host machine. |



### Inital Startup Checklist

This creates a non-superuser account for the mqtt integration script to use.

Note: If you have populated `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_USERNAME` on the first startup you may need to extend these steps with a login.

* Create an empty directory for the containers persistent files. Set USER_ID and GROUP_ID to the ids of the user who owns the directory. Set MONGODB_VOLUME to that directory.

* Spin up the container with blank value for MONGO_USERNAME.

* Create a user for the Python MQTT Integration script. See https://docs.mongodb.com/manual/tutorial/create-users/ for details. Give the user read and write permissions for the database `bemcom_db`. E.g. with this:

  ```
  docker exec -it  your-bemcom-app-mongo-raw-message-db mongo
  use admin
  db.createUser(
  	{
  		user: "bemcom",
  		pwd: passwordPrompt(),
  		roles: [
  			{ role: "readWrite", db: "bemcom_db" }
      	]
  	}
  )
  ```

* Stop the container.

* Set the remaining environment variables (MONGO_USERNAME, MONGO_PASSWORD, MONGO_LOGIN_DB) according to the values you defined previously.

* Restart the container, inspect the logs to verify that everything works as expected.



### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.0.1 | Initial version, some bug while shutting down container.     |
| 0.1.0 | Should be fully functional now. Container shutdown stops everything gracefully now. |
| 0.1.1 | Improve credentials handling.                                |
| 0.2.0 | Update Mongo to 5.0, and allow automatic admin account creation. |

