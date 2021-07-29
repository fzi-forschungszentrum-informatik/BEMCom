# Grafana Tool

This service provides a Grafana instance with a custom plug-in that allows direct data retrieval from REST interface of the Django-API service.

### Configuration

##### Ports

| Port | Usage/Remarks           |
| ---- | ----------------------- |
| 3000 | Default Grafana Ui port |

##### Environment Variables

| Enironment Variable        | Example Value | Usage/Remarks              |
| -------------------------- | ------------- | -------------------------- |
| GF_SECURITY_ADMIN_USER     | admin         | The default admin user     |
| GF_SECURITY_ADMIN_PASSWORD | very!secret&  | The default admin password |

##### Volumes

| Path in Container                          | Usage/Remarks                                                                        |
| ------------------------------------------ | ------------------------------------------------------------------------------------ |
| /var/lib/grafana/grafana.db                | Grafana SQLite database file. Store on local file system to persist grafan settings. |
| /var/lib/grafana/plugins/bemcom-django-api | Allows mounting in the custom plugin. Use for development only.                      |

**Hint**: Add custom volumes to persist changes in Grafana.

### Usage Instructions

##### Initial Setup

- Ensure that the `${GRAFANA_DB_FILE}` exists and has read/write permissions for the user running the container.

##### Data source configuration

The datasource is configured by providing the following settings:

- required:
  - `Name` of the datasource inside grafana
  - `url` to the APIs root. For example `http://django-api.example.com:8000/`
- optional:
  - `use basic authentication`
  - `basicAuth user`
  - `basicAuth password`
  - `skip TLS verification` - check this to ignore self signed certificates <br>
    **important** this option renders https insecure. To enable verification and security a custom CA Authority for verification of certificates is needed.

##### Query configuration

A query can either display meta data on the API or timeseries data.

**Meta data** is toggled by a switch. The received table-like data gives information on all available datapoints.

**Timeseries data** can be of the above described data types.

- Simply choose the datapoint by its short name and the datatype.
  The dropdown also features an autoselection when typing. <br>
- Optionally you can define a frequency of the queried entries and an offset of the frequency to define the time range over which the average is taken.
  Warning: This option is not implemented in BEMCom, yet (Juli 2021). <br>
- A custom name and scaling factor can optionally be defined. Click "apply" or press enter to commit changes here.

### Development

The plugin is written in typescript and based on the [grafana plugin creator and tutorial](https://grafana.com/tutorials/build-a-data-source-plugin/).

You need to have node.js and yarn installed for the following commands. If you have conda installed you can install these with:

```bash
conda create -n node -c conda-forge nodejs==12.* yarn
```

To see your changes in a local grafana instance, change the `docker-compose.yml` file to development mode (see comments in the file) and start grafana as docker container.

Then, to actually work on the plugin:

- Install all needed modules for development from within the `bemcom-django-api` folder with <br>
  `yarn install`
- Make your changes to the source files under `./source/grafana_plugins/bemcom-django-api/src`
- Hot build the plugin to see changes in the browser on reload with `yarn dev --watch`
- Run the tests with `yarn test`
- Build the plugin for production with `yarn build`

Once finished with developing do:

- Update the image tag in [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image.
- Document your changes and new tag by appending the list below.
- git add, commit and push.

Further instructions about working with Grafana:

- [Build a data source plugin tutorial](https://grafana.com/tutorials/build-a-data-source-plugin)
- [Grafana documentation](https://grafana.com/docs/)
- [Grafana Tutorials](https://grafana.com/tutorials/) - Grafana Tutorials are step-by-step guides that help you make the most of Grafana
- [Grafana UI Library](https://developers.grafana.com/ui) - UI components to help you build interfaces using Grafana Design System

### Changelog

| Tag   | Changes                                                                                                                   |
| ----- | ------------------------------------------------------------------------------------------------------------------------- |
| 0.1.0 | Initial version                                                                                                           |
| 0.1.1 | Simpler setpoint selection                                                                                                |
| 0.1.2 | Basic authentication enabled. Skipping TLS verification enabled for self signed certificates.                             |
| 0.1.3 | Additional fields for custom name, scaling factor and datapoint description                                               |
| 0.1.4 | Optional query fields for selecting a frequency and an offset. Define a query-entry limit to prevent BEMCom from crashing |
