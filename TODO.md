# ToDos

* [ ] Documentation

  * [ ] Add more sophisticated example on application creation
    * [ ] Uses demo device and REST connector.
    * [ ] Contains docker-compose file and .env file
    * [ ] Instructions:
      * [ ] How to create application.
      * [ ] Building locally vs Dockerhub
      * [ ] How to use the AdminUI
      * [ ] how to use the API.
    * [ ] Interactive version with Play With Docker?

* [ ] Services

  * [ ] API
    * [ ] Django
      * [ ] Implement Websocket incl. Docs
      * [ ] Service Documentation.
      * [ ] Some ToDos left in Code?
      * [ ] Move from PG to TimescaleDB?
      * [ ] Store Bools in dedicated Field, like the Floats? (Also consider the datapoint type here?)
      * [ ] Expose Prometheus Metrics.
      * [ ] Remove Delete Confirmation
  * [ ] Connectors
    * [ ] REST Connector
      * [ ] Implement in Python, match the Demo Device.
      * [ ] Add documentation.
    * [ ] MQTT Connector.
      * [ ] Fix  issues here with push to raw message DB.
  * [ ] Controllers
    * [ ] Python
      * [ ] Rename to something more goal oriented, i.e. that describes rather what the controller does.
  * [ ] Monitors:
    * [ ] Move MQTT message monitor to Tools
  * [ ] Tools
    * [ ] Demo Device
      * [ ] Implement in FastAPI
      * [ ] Should contain some sensor and some actuator data points.
