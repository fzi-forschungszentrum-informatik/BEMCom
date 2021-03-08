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

| Path in Container                | Usage/Remarks                                                |
| -------------------------------- | ------------------------------------------------------------ |
| /graf_data/plugins/holl-rest-api | Allows mounting in the custom plugin. Use for development only. |

**Hint**: Add custom volumes to persist changes in Grafana.

### On the holl-rest-api plugin

#### Data source configuration

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

#### Query configuration

A query can either display meta data on the API or timeseries data.

**Meta data** is toggled by a switch. The received table-like data gives information on all available datapoints.

**Timeseries data** can be of the above described data types. Simply choose the datapoint by its short name and the datatype.
The dropdown also features an autoselection when typing.

#### Development

The plugin is written in typescript and based on the [grafana plugin creator and tutorial](https://grafana.com/tutorials/build-a-data-source-plugin/).

You can...

- Install all needed modules for development from within the `holl-rest-api` folder with <br>
  `npm install`
- Make your changes to the source files under `./graf_data/plugins/holl-rest-api/src`
- Hot build the plugin to see changes in the browser on reload with `yarn dev --watch`
- Build the plugin for production with `yarn build`

### Changelog

| Tag   | Changes                                                                                       |
| ----- | --------------------------------------------------------------------------------------------- |
| 0.1.0 | Initial version                                                                               |
| 0.1.1 | Simpler setpoint selection                                                                    |
| 1.0.0 | Basic authentication enabled. Skipping TLS verification enabled for self signed certificates. |
