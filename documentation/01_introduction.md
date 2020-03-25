# Introduction

**BEMCom**, the **B**uilding **E**nergy **M**anagement **Com**munication framework, is a software framework for the rapid creation of applications that allow communicating with diverse sensors, actuators and other data sources (e.g webservices). BEMCom was initially designed as a support tool for scientific research projects on building energy management at the [FZI Research Center for Information Technology](https://www.fzi.de/en/about-us/) where the following setting was observed:

* Research projects should optimize the energy consumption patterns of buildings.
* Integration of 100+ distributed and heterogeneous sensor and actuator devices may be required. 
* It is regularly not possible to chose which devices can be used, instead it is necessary to integrate whatever device is already in the building relevant for the project.
* Devices communicate over a very limited set of specific (and often proprietary) protocols. 
* Devices often use flawed implementations of protocols or may show unexpected behavior. 

Due to these settings, but in most importantly due to flawed protocol implementations and unexpected behavior, it is in most cases necessary to develop a custom code to to establish communication with a device. BEMCom is thus not a plug and play communication tool, instead it is a framework that should minimize the effort to implement an application that allows communication with several heterogeneous devices and/or data sources via a standardized programming interface.

# Application Concept

<font color="red">TODO: Add notes on actuator controller.</font>

Each created application will consist of several services with different functionalities. Each service will usually be run as a docker container. The following shows the general dataflow in an application.

![service_concept](graphics/service_concept.png)

As already mentioned, the general purpose of BEMCom is to connect **devices** (or other data sources) to a central interface. Devices are represented as **sensor and actuator** datapoints, whereby one datapoint represents one value. Devices may use any form of communication. If the communication is not Ethernet based, it is necessary to use **hardware gateways**, that are devices that translate the device specific communication to Ethernet. An example could be Bluetooth room sensor (the device) that has two datapoints, e.g. the measured values for humidity and temperature. In order connect the device to the application a Raspberry Pi could be used that forwards the measured values from Bluetooth to a TCP socket.

The following group of services are **connectors** which translate the gateway specific message format to the shared message format used by all services directly connected to the message broker. The message will then be sent to the **message broker** which connects the services with each other. As parsing the gateway specific message format by the connector is in most cases a destructive process (in a sense that information is removed and the raw message received from the gateway cannot be restored from the parsed message) it is often useful to store the raw message to in a **raw message database**. Storing the raw messages allows to replay these and ensures thus that the full history sensor data is preserved, even if a connector contained a software bug that introduced errors while parsing the messages of the gateway. Finally the central **API** and admin interface provides external access to devices and data sources as well as administration user interface to allow configuration of the application and in particular the connectors. Returning to our example, a connector would listen to the gatway's TCP socket and convert incoming messages to the defined message format and sends them via MQTT to the message broker. External applications, like e.g. a user interface for humans interacting with a building, could access the sensor data via the REST interface of the API service.

# Design Concepts

The following design concepts have been applied to BEMCom:

* Reduce system complexity (and thus training period for developers) by isolating components (service oriented architecture).
* Communication between services based on a small set of well defined messages supports development and debugging (as live communication can be inspected).
* Embrace and integrate well established and mature open source components (regardless of the used programming language) to reduce development effort.
* Run each component in a docker container to support failure resilience and scalability of the system.