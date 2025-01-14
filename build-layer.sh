#!/bin/bash

# Create a directory for the layer
mkdir -p .aws-sam/build/python

# Install dependencies into the layer directory
pip install -r requirements.txt -t .aws-sam/build/python

# Build the SAM application
sam build 