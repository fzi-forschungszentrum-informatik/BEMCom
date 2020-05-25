FROM python:3

ENV PYTHONUNBUFFERED 1

# Create the required folder structure and give any user read/write
# access as the container may be run with arbitrary user_id to prevent
# file permission errors on the host.
RUN mkdir -p /bemcom/code && \
    chmod a+rw -R /bemcom
WORKDIR /bemcom

# Install dependencies
COPY ./requirements.txt /bemcom/
RUN pip install -r requirements.txt

# Install source code.
COPY ./code/ /bemcom/code/

# Add entrypoint script for container init.
COPY ./entrypoint.sh /bemcom/
CMD ["bash","/bemcom/entrypoint.sh"]
