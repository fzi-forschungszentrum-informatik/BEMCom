# This is a multistage build that creates a base layer that contains
# all the stuff the container needs anyways, and uses and intermediate
# layer to execute the tests but without storing the results.
# This packages uses micromamba as it seems to be faster and smaller then
# the conda docker container. See this repo for details:
# https://github.com/mamba-org/micromamba-docker
#
FROM mambaorg/micromamba:0.22.0 as base

# This allows to install the dependencies of the service-template
# before the actual code, which decouples these in the docker layers.
# This makes up-/downloading the images and building faster.
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install --yes --file /tmp/environment.yml && \
    micromamba clean --all --yes && \
    rm /tmp/environment.yml

# Create a directory with write permission for installation of services.
USER root
RUN mkdir -p /source/ && \
    chown $MAMBA_USER:$MAMBA_USER /source/ && \
    chmod a+rwx /source/

# Install auto-pytest script.
COPY auto-pytest.sh /usr/bin/auto-pytest
RUN chmod a+rx /usr/bin/auto-pytest

# Make it cozy for the user of the container.
USER $MAMBA_USER
WORKDIR /source/


FROM base AS tester
# Again start with installing the depdencies for the tests to keep the
# results in Docker's build cache.
COPY --chown=$MAMBA_USER:$MAMBA_USER additional_dependencies_for_some_tests.yml \
 /tmp/additional_dependencies_for_some_tests.yml
RUN micromamba update --yes --file /tmp/additional_dependencies_for_some_tests.yml

# Activating a conda environment for RUN commands
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Manually install dependencies not available as conda package, seems like mamba
# has a bug here in parsing the environment file. 
RUN pip install django-timescaledb==0.2.11

# Install the package and tests.
RUN mkdir -p /source/energy_service_generics/
COPY --chown=$MAMBA_USER:$MAMBA_USER esg /source/energy_service_generics/esg
COPY --chown=$MAMBA_USER:$MAMBA_USER tests /source/energy_service_generics/tests
COPY --chown=$MAMBA_USER:$MAMBA_USER setup.py /source/energy_service_generics/setup.py
RUN pip install /source/energy_service_generics

# Run tests, these should only need the installed package.
RUN pytest /source/energy_service_generics/


FROM base AS final
# Activating a conda environment for RUN commands
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Copy the installed pacakges.
COPY --from=tester /opt/conda/lib/python3.10/site-packages/esg \
  /opt/conda/lib/python3.10/site-packages/esg

# This will make the build fail if the module cannot be imported.
RUN python -c "import esg; print('ESG version: {}'.format(esg.__version__))"
