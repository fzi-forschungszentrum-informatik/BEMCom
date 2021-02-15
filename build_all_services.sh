#!/bin/bash
set -e

# Finds the absolute bath of the build scripts. Starts with the service_templates
# first as these docker images might be required to build the services.
for dir in service_templates services
do
    find $dir -name build_docker_image.sh -exec readlink -f {} \;| while read build_script
    do
        # And executes the build scripts in the correct directory to make local paths work.
        script_dir=$(echo "$build_script" | rev | cut -d / -f2-1000 | rev)
        # Skip the build scripts in the starter kits of the connector templates.
        # These don't contain useful BEMCom images.
        if [[ $script_dir == *"starter-kit"* ]]; then
            continue
        fi
        cd "$script_dir"
        printf "Running $build_script"
        # Preserve log output so we can only display output that failed.
        {
            build_out=$(bash build_docker_image.sh 2>&1) &&
            echo -e "\e[1;32m OK \e[0m"
        } || {
            # This is only executed on error. Exit the script after printing what failed.
            echo -e "\e[1;31m Failed! \e[0m"
            printf "\nLog was:\n\n$build_out\n\n"
            exit 1    
        }
    done
done
