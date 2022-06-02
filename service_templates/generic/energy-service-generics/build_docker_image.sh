TAG=$(cat source/esg/_version.py | grep "__version__ =" | cut -d "=" -f 2 | xargs )
docker build ./source -t bemcom/energy-service-generics:$TAG
