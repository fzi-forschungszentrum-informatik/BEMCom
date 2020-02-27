#!/bin/bash
set -e

# Finds the absolute bath of the build scripts
find . -name build_docker_image.sh -exec readlink -f {} \;| while read build_script
do
    # And executes the build scripts in the correct directory to make local paths work.
    script_dir=$(echo "$build_script" | rev | cut -d / -f2-1000 | rev)
    cd "$script_dir"
    bash build_docker_image.sh
done
