# Execute the application_builder, a python script, in it's runtime
# environment, that is a docker container off course.

# This is the absolute directory of this script, it allows calls to
# the script from other paths too.
# This solution is rather portable and does not rely on realpath
# which does not exists on all linux distros.
ROOTDIR="$(cd "$(dirname "$0")" && pwd)"

# Current image label and version of the runtime environment.
IMAGE_LABEL="application-builder_runtime"
IMAGE_VERSION="0.0.1"

# Check if the image exists already.
if [[ "$(docker images -q $IMAGE_LABEL:$IMAGE_VERSION 2> /dev/null)" == "" ]]; then

    # Check if older images (with other version tags) exist
    if [[ ! "$(docker images -q $IMAGE_LABEL 2> /dev/null)" == "" ]]; then
        echo "##################################################################"
        echo "Removing images of old versions of the runtime environment."
        echo "##################################################################"
        echo
        # Iterate containers, uniq prevents attempting to remove the same image twice
        # E.g. if the same image has multiple tags.
        docker images -q $IMAGE_LABEL | uniq | while read container_id; do 
            docker image rm -f $container_id
        done
    fi

    echo
    echo "##################################################################"
    echo "Building docker image for runtime environment."
    echo "##################################################################"
    echo
    DOCKERFILE_CONTEXT="$ROOTDIR"
    docker build -t $IMAGE_LABEL:$IMAGE_VERSION $DOCKERFILE_CONTEXT
fi

echo
echo "##################################################################"
echo "Starting application_builder."
echo "##################################################################"
echo

# Locate the path of the python code for the mount below.
PYTHON_CODE_DIR="$ROOTDIR/python_code"

# Start the runtime environment and pass arguments.
# --rm removes the container after it is run.
# --name is nicer for inspection if something goes wrong and ensures that
#        the script is run singleton only.
# --user prevents permission denied errors while accessing the code and
# ensures that everything within the container has no higher privileges
# then the current user.
docker run --rm \
           --name $IMAGE_LABEL \
           --volume "$PYTHON_CODE_DIR:/code" \
           --user "$(id -u):$(id -g)" \
           $IMAGE_LABEL:$IMAGE_VERSION python /code/main.py $@
