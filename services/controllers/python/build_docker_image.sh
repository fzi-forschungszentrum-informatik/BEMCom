TAG=$(cat source/code/controller.py | grep "__version__ = " | cut -d "=" -f 2 | tr -d '" ' )
docker build ./source -t bemcom/python-controller:$TAG
