FROM bemcom/python-connector-template:0.8.0

ENV PYTHONUNBUFFERED=1

# Create the required folder structure and give any user read/write
# access as the container may be run with arbitrary user_id to prevent
# file permission errors on the host.
RUN mkdir -p /bemcom/code && \
    chmod a+rw -R /bemcom
WORKDIR /bemcom

# Currently no dependencies that are not already
# satisfied by python-connector-template
# # Install dependencies
# COPY ./requirements.txt /bemcom/
# RUN pip install -r requirements.txt

# Install source code.
COPY ./code/ /bemcom/code/
RUN chmod a+rwx -R /bemcom/code

# Add entrypoint script for container init.
COPY ./entrypoint.sh /bemcom/
ENTRYPOINT ["bash", "/bemcom/entrypoint.sh"]
