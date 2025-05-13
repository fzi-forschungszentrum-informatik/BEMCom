# psutil needs gcc to be built but we don't want to have gcc
# in the final image needs roughly 250MiB.
FROM bemcom/python-connector-template:0.8.0 AS builder

RUN apt-get update && apt-get install gcc -y

# Installs dependencies.
COPY ./requirements.txt /source/requirements.txt
RUN pip install -r /source/requirements.txt

FROM bemcom/python-connector-template:0.8.0

# Copy over dependencies form builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Export your connector script. Ensure the main program of the
# connector resides under ./source/connector/main.py
COPY ./connector/ /source/connector/

# Run all tests to verify the connector is ok.
RUN pytest /source/connector/
