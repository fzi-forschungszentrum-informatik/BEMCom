FROM python:3.8

# Install the pyconnector package.
COPY pyconnector_template/ setup.py /source/pyconnector_template/
COPY setup.py /source/
RUN pip install /source/ &&\
    rm -rf /source/pyconnector_template /source/setup.py

# Add the entrypoint script to run as default.
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/docker-entrypoint.sh
CMD ["docker-entrypoint.sh"]
