FROM bemcom/python-connector-template:0.1.2

# Installs dependencies.
COPY ./requirements.txt /soucrce/requirements.txt
RUN pip install -r /soucrce/requirements.txt

# Export your connector script. Ensure the main program of the
# connector resides under ./source/connector/main.py
COPY ./connector/ /source/connector/




