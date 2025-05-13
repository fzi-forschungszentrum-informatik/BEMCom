# This script assumes that docker is configured with a builder that can 
# build multi-platform images. These commands may help you create such:
# docker buildx create --name bemcom_builder --use
# docker buildx inspect --bootstrap
# See also:
# https://docs.docker.com/build/building/multi-platform/
VERSION=$(pdm show -p source --version)
printf "\033[0;31m" # make red
read -p "Building and pushing version '$VERSION'. Are you sure? (y/n) " yn
printf "\033[0m" # no color.
case $yn in 
	y ) echo Starting build.;;
	* ) echo Exiting.;
		exit;;
esac

docker buildx build --push --platform linux/arm/v7,linux/amd64 ./source -t bemcom/python-connector-template:$VERSION