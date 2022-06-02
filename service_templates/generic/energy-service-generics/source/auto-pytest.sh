#!/bin/bash
#
# A simple wrapper that automatically runs pytest on every file change.
# All input arguments are forwarded to pytest.
#
/opt/conda/bin/watchmedo auto-restart \
  --directory=/source/ \
  --patterns="*.py" \
  --recursive \
  -- /opt/conda/bin/pytest $@
