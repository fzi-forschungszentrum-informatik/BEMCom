# Node-RED Connector Template

This template allows the the implementation of connectors in Node-RED with maximum efficiency, as all generic components of the connector are already provided in the template, that is all functionality that is not specific to the devices that should be linked with the connector to BEMCom.

### Checklist for Creating a New Connector

* [ ] Copy the files from the [starter-kit](./starter-kit) folder into a new directory.
* [ ] Edit your copy of [starter-kit/docker-compose.yml](starter-kit/docker-compose.yml) file as needed. It is intended to to start the new connector service during development of it. See some of the other connectors for an example.
* [ ] Implement the logic of the connector following the process described in [starter-kit/Readme.md](starter-kit/Readme.md). Be aware that the nodes in the  `Main` flow provide additional documentation so check the node information for more details. Consider to to document the flows you create by also providing node information and human friendly node names. 
* [ ] Document the connector by extending your copy [starter-kit/Readme.md](starter-kit/Readme.md).
* [ ] Update the name of the connector and the current version number in your copy of [starter-kit/build_docker_image.sh](starter-kit/build_docker_image.sh).

###  Checklist for Updating the Template

* [ ] Check that your user-id matches the currently configured user-id in [docker-compose.yml](docker-compose.yml), and use docker-compose to start the development container.
* [ ] Implement your changes.
* [ ] Update the version number in [build_docker_image.sh](build_docker_image.sh) and in  [starter-kit/source/Dockerfile](starter-kit/source/Dockerfile).
* [ ] Check if your changes affect [starter-kit/docker-compose.yml](starter-kit/docker-compose.yml), [starter-kit/Readme.md](starter-kit/Readme.md) or [starter-kit/build_docker_image.sh](starter-kit/build_docker_image.sh).
* [ ] Check if it is necessary to update existing connectors, by editing the respective Dockerfile in their source directory.  You may need to build the template first.

### Changelog

| Tag   | Changes                   |
| ----- | ------------------------- |
| 0.1.0 | First productive version. |

