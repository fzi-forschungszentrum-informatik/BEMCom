FROM python:3

ENV PYTHONUNBUFFERED 1

# Create the required folder structure.
RUN mkdir -p /source/api /source/static

WORKDIR /source

# Install dependencies
COPY ./requirements.txt /source/
RUN pip install -r requirements.txt

# Install source code.
COPY ./api/ /source/api/

# Add entrypoint script for container init.
COPY ./entrypoint.sh /source/
CMD ["bash","/source/entrypoint.sh"]

# Run all tests to verify the service is ok.
RUN MQTT_BROKER_HOST=localhost DJANGO_SECRET_KEY=s pytest /source/api/

# Grant all users read/write permissions to the source folder.
# This allows running the container with arbitrary user/group ids.
# This must be here at the very end to also affect the empty sqlite
# file created during the test execution.
RUN chmod a+rw -R /source
