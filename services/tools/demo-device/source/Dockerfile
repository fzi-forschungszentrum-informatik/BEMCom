FROM python:3.8

# Installs dependencies.
COPY ./requirements.txt /source/requirements.txt
RUN pip install -r /source/requirements.txt

# Copy the source code of the demo-devoce
COPY ./demo-device/ /source/demo-device/

# Add the entrypoint script to run as default.
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
