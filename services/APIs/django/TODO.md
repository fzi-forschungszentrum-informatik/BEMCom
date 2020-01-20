# Open Tasks

* [ ] Extend ConnectorMQTTIntegration to listen to incoming messages.
* [ ] Add HTML elements Datapoint.
* [ ] Add Websocket update procedures.
* [ ] Build datapoint_map after changes to Datapoints.
* [ ] Integrate with Databases
  * [ ] Docker files for Mongo Value DB
  * [ ] Docker files for InfluxDB
  * [ ] DB Management in Django Admin
  * [ ] Replay functionality for raw message DB.
  * [ ] Query messages integrated into Django.
* [ ] Add some comment field (maybe as tags?) to the Datapoint model.
* [ ] Add filter to Datapoint to filter for example value, for empty, not-empty, numeric, non-numeric. 
* [ ] Add some convenience function to Datapoint that allows a faster retrieval of the DatapointAddition model and list of it's fields. 
* [ ] Add last_value and last_timestamp to list view of Datapoint.
* [ ] Note in documentation that Datapoint addition should always have last_value and last_timestamp fields?
