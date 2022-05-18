FROM iik-gitlab.fzi.de:5050/dwo/energy-service-generics:0.12.0

ENV PYTHONUNBUFFERED 1

# Create the required folder structure.
RUN mkdir -p /source/emp-link

WORKDIR /source

# Install dependencies first, makes subsequent builds faster.
COPY ./requirements.txt /source/emp-link/requirements.txt
RUN /opt/conda/bin/pip install -r /source/emp-link/requirements.txt

# Install source code.
COPY --chown=$MAMBA_USER:$MAMBA_USER . /source/emp-link/

# Start the service by default on container startup.
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "bash", "/source/emp-link/entrypoint.sh"]
