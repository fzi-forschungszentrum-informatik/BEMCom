FROM python:3.12-slim

# Install the pyconnector package.
COPY pyconnector_template /source/pyconnector_template/pyconnector_template
COPY tests /source/pyconnector_template/tests
COPY pyproject.toml /source/pyconnector_template/pyproject.toml

# Install (-e preserves a bit of file size).
RUN pip install -e /source/pyconnector_template

# Run tests, these should only need the installed package.
RUN pytest /source/pyconnector_template/

# Add the entrypoint script to run as default.
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
