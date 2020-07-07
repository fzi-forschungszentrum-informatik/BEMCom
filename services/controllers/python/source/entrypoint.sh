#!/bin/
set -e

# Run tests for the log to see if we expect the controller to work properly
cd /bemcom
#pytest /bemcom/code/

# Start up the controller.
ls -la /bemcom/code
python3 /bemcom/code/controller.py
