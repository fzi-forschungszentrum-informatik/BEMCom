 FROM bemcom/python-connector-template:0.6.0

ENV PYTHONUNBUFFERED=1

# Create the required folder structure.
RUN mkdir -p /source/emp-link

WORKDIR /source

# Install dependencies first, makes subsequent builds faster.
COPY ./requirements.txt /source/emp-link/requirements.txt
RUN pip install -r /source/emp-link/requirements.txt

# Fetch the latest version of energy-service-generics. Note that we don't use
# this image directly as base image because:
# 1. It is rather large and contains a lot of packages we don't need.
# 2. It depends on an image for which no arm-v7 version is available, 
#    but this is required to deploy to RaspberryPI.
# Copy the installed pacakges.
COPY --from=bemcom/energy-service-generics:0.12.3 /opt/conda/lib/python3.10/site-packages/esg \
  /usr/local/lib/python3.10/site-packages/esg

# Install source code.
COPY . /source/emp-link/

# Start the service by default on container startup.
ENTRYPOINT ["bash", "/source/emp-link/entrypoint.sh"]
