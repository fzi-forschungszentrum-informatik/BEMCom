FROM python:3

ENV PYTHONUNBUFFERED 1

# Create the required folder structure and give any user read/write
# access as the container may be run with arbitrary user_id to prevent
# file permission errors on the host.
# Also Add folder where the SQLite DB should be stored.
# This must be a folder due to the journaling files created
# by SQLite. This folder should be overloaded by a volume 
# mount in production, but serves as fallback this is not configured.
RUN mkdir -p /source/code /source/static /source/cert && \
    chmod a+rw -R /source
WORKDIR /source

# Install dependencies
COPY ./requirements.txt /source/
RUN pip install -r requirements.txt

# Install source code.
COPY ./code/ /source/code/

# Add entrypoint script for container init.
COPY ./entrypoint.sh /source/
CMD ["bash","/source/entrypoint.sh"]

# Run all tests to verify the service is ok.
RUN pytest /source/code/
