TAG=$(cat source/connector/main.py | grep "__version__ = " | cut -d "=" -f 2 | tr -d '" ' )
docker build ./source -t bemcom/modbus-tcp-connector:$TAG
