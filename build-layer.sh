#!/bin/bash

# Create layer directory structure
mkdir -p layer/python

# Install dependencies into layer
pip3 install -t layer/python \
    spacy==3.5.0 \
    allennlp==2.10.1 \
    allennlp-models==2.10.1

# Create layer zip
cd layer
zip -r ../nlp-layer.zip .
cd ..

# Clean up
rm -rf layer 