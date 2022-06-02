#!/bin/bash
set -e
set -u

echo "Entering entrypoint.sh"
if [ "${AUTO_RELOAD:-FALSE}" == "TRUE" ]
then
    watchmedo auto-restart \
      --directory=/source/emp-link/ \
      --patterns="*.py" \
      --recursive \
      -- python3 /source/emp-link/main.py
else
    python3 /source/emp-link/main.py
fi
