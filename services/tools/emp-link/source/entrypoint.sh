#!/bin/bash
set -e
set -u

echo "Entering entrypoint.sh"
if [ "${AUTO_RELOAD:-FALSE}" == "TRUE" ]
then
    /opt/conda/bin/watchmedo auto-restart \
      --directory=/source/emp-link/ \
      --patterns="*.py" \
      --recursive \
      -- /opt/conda/bin/python3 /source/emp-link/main.py
else
    /opt/conda/bin/python3 /source/emp-link/main.py
fi
