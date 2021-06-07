FROM bemcom/python-connector-template:0.3.1

# Installs dependencies.
COPY ./requirements.txt /source/requirements.txt
RUN pip install -r /source/requirements.txt

# Export your connector script. Ensure the main program of the
# connector resides under ./source/connector/main.py
COPY ./connector/ /source/connector/

# Run all tests to verify the connector is ok.
RUN pytest /source/connector/
