FROM grafana/grafana:7.3.6

# Sets the plugins directory out of the main data dircectory (/var/lib/grafana by default).
# Else the plugins would be overwritten while mounting the /var/lib/grafana directory.
ENV GF_PATHS_PLUGINS=/var/lib/grafana-plugins

# Install the plugins
COPY ./grafana_plugins/bemcom-django-api/dist /var/lib/grafana-plugins/bemcom-django-api
COPY ./grafana_plugins/nwpdata-service-api/dist /var/lib/grafana-plugins/nwpdata-service-api
COPY ./grafana_plugins/prediction-service-api/dist /var/lib/grafana-plugins/prediction-service-api

