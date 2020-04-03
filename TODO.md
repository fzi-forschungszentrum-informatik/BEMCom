# Track to OS Release

* [ ] Repo root
  * [ ] Make build script process connector templates first
  * [ ] Add license
  * [ ] Update Readme
  * [ ] Remove application_builder, applications and application_templates folders
* [ ] Demo
  * [ ] Move demo folder to root
  * [ ] docker compose file
  * [ ] Instructions how to build
  * [ ] Instructions how to use the API.
  * [ ] Instructions how to modify a Node-RED connector.
* [ ] Documentation
  * [ ] Dependencies (Docker, ..)
  * [ ] Building locally vs Dockerhub
  * [ ] Message Format
  * [ ] High Level Introduction to components.
* [ ] Services
  * [ ] API
    * [ ] REST API pull
    * [ ] REST API push incl. Docs
    * [ ] Token authentication and access control
    * [ ] Prod Settings (Daphne, Debug, PG Database, HTTPs, self signed certs?)
    * [ ] Service Documentation.
  * [ ] Connectors
    * [ ] Aquametro
      * [ ] Service Documentation
    * [ ] Keba
      * [ ] Service Documentation
    * [ ] Demo
      * [ ] Implement in Node Red
      * [ ] Two datapoints, one that yields current time as str, one that ping/pongs with delay.
      * [ ] Service Documentation
  * [ ] Controller
    * [ ] Service Documentation
    * [ ] Implementation
  * [ ] Raw Message DB
    * [ ] Implement with Mongo + Python script to connect to MQTT.
    * [ ] Service Documentation
  * [ ] Message Broker Monitor
    * [ ] Service Documentation
    * [ ] Rename to something with Node-RED
* [ ] Service Templates
  * [ ] Connectors
    * [ ] Python
      * [ ] Move to devl branch
    * [ ] Node Red
      * [ ] Update documentation (How to)

