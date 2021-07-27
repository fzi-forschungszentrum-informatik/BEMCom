# Creating BEMCom Applications

Recalling the [application concept](./01_concepts.md), it is apparent that a functional and building specific HAL instance will require one API service (including the metadata database), one message broker, one or more connector services, and optionally a raw message database service. The BEMCom repository provides fully functional implementations of an API service, a message broker and a raw message database which should be sufficient for most applications, thus effectively removing the burden of implementing these services from the user. It is worth noting that the provided implementation of the API service exposes a secure REST interface for external components, supporting user authentication and HTTPS for encryption. All available services, including a number of connector services, can be found in the [services](../services/) folder in this repository.

Leveraging the design concepts of BEMCom, i.e. the service oriented approach and the execution of services as Docker containers, creating an application is reduced to simply configuring and starting the selected services. A minimal example for setting up a service is the following line of shell code that can be used  on any machine having docker installed:
```
docker run -p 1883:1883 bemcom/mosquitto-mqtt-broker:0.1.0
```
This code starts a message broker service which is required for any BEMCom application to allow the remaining services to communicate with each other, and configures the broker to accept incoming connections on port 1883, the default value for the MQTT protocol. In order to let the above example become a functional BEMCom application it would be necessary to also start an API service and a connector service. More sophisticated examples will be added at a later point in time.

