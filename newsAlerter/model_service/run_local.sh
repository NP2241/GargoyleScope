#!/bin/bash

# Build and run the model service locally
docker build -t deepseek-sentiment .
docker run -d -p 8080:8080 --name deepseek-sentiment-local deepseek-sentiment 