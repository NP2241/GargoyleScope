#!/bin/bash

# Create a Docker volume for model persistence if it doesn't exist
docker volume create model-cache

# Build with the volume mounted
sam build --debug --parameter-overrides \
  DockerBuildArgs="--mount type=volume,source=model-cache,target=/var/task/model"

# Clean up old images but keep the volume
docker system prune -f 