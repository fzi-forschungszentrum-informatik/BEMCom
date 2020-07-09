# Track to OS Release

* [ ] Repo root
  * [x] Make build script process connector templates first
  * [ ] Add test stages to pipeline
  * [ ] Add license
  * [ ] Update Readme
  * [x] Remove application_builder, applications and application_templates folders
* [ ] Demo
  * [x] Move demo folder to root
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
    * [x] REST API pull
    * [ ] REST API push incl. Docs
    * [ ] Token authentication and access control
    * [x] Prod Settings (Daphne, Debug, PG Database, HTTPs, self signed certs?)
    * [ ] Service Documentation.
    * [x] OpenAPI specification of REST API.
    * [x] Define control groups in admin.
  * [ ] Connectors
    * [x] Aquametro
      * [x] Service Documentation
    * [x] Keba
      * [x] Service Documentation
    * [ ] Demo
      * [ ] Implement in Node Red
      * [ ] Two datapoints, one that yields current time as str, one that ping/pongs with delay.
      * [ ] Service Documentation
  * [x] Controller
    * [x] Service Documentation
    * [x] Implementation
  * [x] Raw Message DB
    * [x] Implement with Mongo + Python script to connect to MQTT.
    * [x] Service Documentation
    * [x] Fix auth bug
  * [x] Message Broker Monitor
    * [x] Service Documentation
    * [x] Rename to mqtt-message-montior
* [x] Service Templates
  * [x] Connectors
    * [x] Python
      * [x] Move to devl branch
    * [x] Node Red
      * [x] Update documentation (How to)
      * [x] Update docker-compose order of fields.

