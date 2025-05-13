VERSION=$(pdm show -p source --version)
docker build ./source -t bemcom/python-connector-template:$VERSION
