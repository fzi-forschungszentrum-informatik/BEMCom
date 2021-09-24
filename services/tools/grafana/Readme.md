# Grafana Tool

This service provides a Grafana instance with custom plug-ins that allow:

- `bemcom-django-api`:  Data retrieval from the REST interface of the BEMCom Django-API service.
- `prediction-service-api`: Request and display data provided via the prediction service REST API.
- `nwpdata-service-api`: Request and display of data provided via the nwpdata service REST API.

Please note that the prediction service and nwpdata service REST API have not been published to the public yet. You can simple ignore these plugins thus.

### Configuration

##### Ports

| Port | Usage/Remarks           |
| ---- | ----------------------- |
| 3000 | Default Grafana Ui port |

##### Environment Variables

| Enironment Variable        | Example Value | Usage/Remarks                                    |
| -------------------------- | ------------- | ------------------------------------------------ |
| GF_SECURITY_ADMIN_USER     | admin         | The default admin user. Defaults to `bemcom`     |
| GF_SECURITY_ADMIN_PASSWORD | very!secret&  | The default admin password. Defaults to `bemcom` |

##### Volumes

| Path in Container                               | Usage/Remarks                                                |
| ----------------------------------------------- | ------------------------------------------------------------ |
| /var/lib/grafana/grafana.db                     | Grafana SQLite database file. Store on local file system to persist grafan settings. |
| /var/lib/grafana-plugins/bemcom-django-api      | Allows mounting in the custom plugin. Use for development only. |
| /var/lib/grafana-plugins/nwpdata-service-api    | Allows mounting in the custom plugin. Use for development only. |
| /var/lib/grafana-plugins/prediction-service-api | Allows mounting in the custom plugin. Use for development only. |

**Hint**: Add custom volumes to persist changes in Grafana.

### Usage Instructions

##### Initial Setup

- Ensure that the `${GRAFANA_DB_FILE}` exists and has read/write permissions for the user running the container.

##### Data source configuration

The datasources are configured by providing the following settings:

- required:
  - `Name` of the datasource inside grafana
  - `url` to the APIs root. For example `http://django-api.example.com:8000/`
- optional:
  - `use basic authentication`
  - `basicAuth user`
  - `basicAuth password`
  - `skip TLS verification` - check this to ignore self signed certificates.
    **important** this option renders https insecure. To enable verification and security a custom CA Authority for verification of certificates is needed.

Optional settings are initally only of importance to the BEMCom API.

##### Query configuration

###### BEMCOM API plugin

A query can either display meta data on the API or timeseries data.

**Meta data** is toggled by a switch. The received table-like data gives information on all available datapoints.

**Timeseries data** can be of the above described data types.

- Simply choose the datapoint by its short name and the datatype.
  The dropdown also features an autoselection when typing. <br>
- Optionally you can define a frequency of the queried entries and an offset of the frequency to define the time range over which the average is taken.
  Warning: This option is not implemented in BEMCom, yet (Juli 2021). <br>
- A custom name and scaling factor can optionally be defined. Click "apply" or press enter to commit changes here.

###### Nwpdata and stochastic prediction service API plugin

Use the textfield to define the parameters needed for the request as JSON string. The actual format depends on the service queried and can be found on the Swagger UI at the root URL of the respective service. The following settings work well with the FZI internal DWD MOSMIX Data Service for example expects parameters as followed:

```bash
{
  "station": "Q712",
  "start_timestamp": $from,
  "end_timestamp": $to,
  "updates": "latest",
  "mosmix_parameters": ["TTT"]
}

```

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

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.1.0 | Initial version                                              |
| 0.1.1 | Simpler setpoint selection                                   |
| 0.1.2 | Basic authentication enabled. Skipping TLS verification enabled for self signed certificates. |
| 0.1.3 | Additional fields for custom name, scaling factor and datapoint description |
| 0.1.4 | Restructured query editor. Optional field to define an offset. Integrate grafana's query option 'interval' |
| 0.2.0 | Added additional plugins for querying nwpdata and stochastic prediction services |
