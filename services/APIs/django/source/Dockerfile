FROM python:3

ENV PYTHONUNBUFFERED 1

# Create workdir
RUN mkdir -p /bemcom/code 
WORKDIR /bemcom

# Install dependencies
COPY ./requirements.txt /bemcom/
RUN pip install -r requirements.txt

# Install source code.
COPY ./django_code/ /bemcom/code/

# Add a fallback file for the SQLite DB that can 
# used if no external file is mounted in.
RUN touch /bemcom/db.sqlite3 && \
    chmod a+rw /bemcom/db.sqlite3

# Add entrypoint script for container init.
COPY ./entrypoint.sh /bemcom/
CMD ["bash","/bemcom/entrypoint.sh"]
