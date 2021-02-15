# Python Connector Template

This template allows the the implementation of connectors in Python with maximum efficiency, as all generic components of the connector are already provided in the template, that is all functionality that is not specific to the devices that should be linked with the connector to BEMCom.

### Checklist for Creating a New Connector

* [ ] Copy the files from the [starter-kit](./starter-kit) folder into a new directory.
* [ ] Edit your copy of [starter-kit/docker-compose.yml](starter-kit/docker-compose.yml) file as needed. It is intended to to start the new connector service during development of it. See some of the other connectors for an example.
* [ ] Implement the logic of the connector following the process described in [starter-kit/Readme.md](starter-kit/Readme.md). Be aware that base classes for developing connectors are provided in [source/pyconnector_template/pyconector_template.py](source/pyconnector_template/pyconector_template.py) and  [source/pyconnector_template/dispatch.py](source/pyconnector_template/dispatch.py), where extensive documentation is provided.
* [ ] Document the connector by extending your copy [starter-kit/Readme.md](starter-kit/Readme.md).
* [ ] Update the name of the connector and the current version number in your copy of [starter-kit/build_docker_image.sh](starter-kit/build_docker_image.sh).

###  Checklist for Updating the Template

* [ ] Implement your changes including tests. The simplest way for developing locally is to install the pyonnector_template package locally with:

  ```
  pip install -e ./source/
  ```

  Ensure that all tests are passed before continuing, the docker image will not build if not.

  ```
  pytest ./source/
  ```

* [ ] Update the version number in [build_docker_image.sh](build_docker_image.sh),in [starter-kit/source/Dockerfile](starter-kit/source/Dockerfile) and [source/setup.py](source/setup.py) 

* [ ] Check if your changes affect [starter-kit/docker-compose.yml](starter-kit/docker-compose.yml), [starter-kit/Readme.md](starter-kit/Readme.md) or [starter-kit/build_docker_image.sh](starter-kit/build_docker_image.sh).

* [ ] Build the template image with:

  ```
  bash build_docker_image.sh
  ```

* [ ] Check if it is necessary to update existing connectors, by editing the respective Dockerfile in their source directory.

### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.1.0 | First productive version.                                    |
| 0.1.1 | Set retain for available_datapoints                          |
| 0.1.2 | Set all loggers to INFO if DEBUG is not set. Improve templates and documentation. |

