# Commands

* create-application: 
  * copy application files. (If not devl)
  * create the docker-compose.yml file of the application.
  * Check that all environment variables are set.
* remove-application: 
  * Calls docker-compose down (removes containers, images, networks) to prevent orphaned docker stuff.
  * Removes all local files of the application.  

## Workflow

* Define a template.
  * Defines which services are used.
  * Defines configuration for these services.
* Call `create-application` on the template to create the local files.
* Go to the directory of the created application an inspect the docker-compose.yml file.
* Run docker-compose up to build the docker images and start the application.
* Use start/stop to start/stop the application
* Use docker-compose down to remove containers, images and networks of the application. This will delete all files/state of the application that is stored in the containers of the service.
* Call remove-application to delete all locally saved files.

