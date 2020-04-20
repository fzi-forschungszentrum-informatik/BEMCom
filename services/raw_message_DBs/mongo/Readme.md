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
| MONGO_INITDB_ROOT_USERNAME  | bemcom-admin        | If set on **first** start of the container with an empty data directory (see [Volumes](#volumes)), will set the username of the root user of the Mongo DB to the specified value.  Check the official documentation of the Mongo docker image for more details. |
| MONGO_INITDB_ROOT_PASSWORD  | very!secret&        | Similar to MONGO_INITDB_ROOT_USERNAME but for the password of the root user. |
| MONGO_USERNAME              | bemcom-user         | The username of the account that is used by the mqtt-integration.py script to connect to the MongoDB. Leave blank if access without authentication is configured. However, if the username is required, it must be set all the time (in contrast to MONGO_INITDB_ROOT_USERNAME) |
| MONGO_PASSWORD              | even_mode:secret&   | Similar to MONGO_USERNAME but for the password of the normal user. |
| MQTT_BROKER_HOST            | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_PORT            | 1883                | The port of the MQTT broker.                                 |
| MQTT_TOPIC_ALL_RAW_MESSAGES | +/raw_message_to_db | The topic on the broker on which the raw messages will be published. Stick to the convention of the example value given here to prevent messy surprises. |
| MQTT_INTEGRATION_LOG_LEVEL  | INFO                | The level of log messages that will be logged to stdout of the container for the mqtt-integration.py script. Can be any of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `Critical`. The Info is reasonable for normal operation. |


##### Volumes

| Path in Container | Usage/Remarks                                                |
| ----------------- | ------------------------------------------------------------ |
| /data/db          | Folder in which MongoDB stores its DB. Is required to persist the Database. The folder on the host machine must exist before the container is run for the first time and the container must be started with the user id of the user who own the folder on the host machine. |



* ### Inital Startup Checklist

  * Create an empty directory for the containers persistent files. Set USER_ID and GROUP_ID to the ids of the user who owns the directory. Set MONGODB_VOLUME to that directory.
  * Set MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD.
  * Spin up the container.
  * Create a user for the Python MQTT Integration script. See https://docs.mongodb.com/manual/tutorial/create-users/ for details. Give the user read and write permissions for the database `bemcom_db`.
  * Stop the container.
  * Set the remaining environment variables.
  * Restart the container, inspect the logs to verify that everything works as expected.



### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.0.1 | Initial version, some bug while shutting down container.     |
| 0.1.0 | Should be fully functional now. Container shutdown stops everything gracefully now. |