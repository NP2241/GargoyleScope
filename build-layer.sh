#!/bin/bash

# Create a fresh build directory
rm -rf build
mkdir -p build

# Create the Python package directory structure
mkdir -p build/python/lib/python3.9/site-packages

# Install dependencies into the package directory
pip3 install --target build/python/lib/python3.9/site-packages \
    nltk==3.8.1 \
    python-dotenv==1.0.0 \
    requests==2.31.0 \
    boto3>=1.26.0 \
    beautifulsoup4==4.12.3

# Create the layer ZIP file
cd build
zip -r ../layer.zip .
cd ..

# Clean up
rm -rf build 