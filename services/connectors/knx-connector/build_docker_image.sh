TAG=$(cat source/connector/main.py | grep "__version__ =" | cut -d "=" -f 2 | xargs )
docker build ./source -t bemcom/knx-connector-image:$TAG
