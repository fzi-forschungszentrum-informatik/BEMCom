FROM bemcom/node-red-connector-template:0.2.1

# Export your flows to the flows folder. They will be installed on startup.
COPY ./flows /flows

# Add the file for storing the usernames/passwords as these will not be
# exported with the normal flow. See Readme.
COPY ./flows_cred.json /data/flows_cred.json

# Place your dependencies here. E.g:
# RUN npm install node-red-node-ui-table@0.2.2


