#!/bin/bash

# Path to input and output directories (on your local machine)
INPUT_DIR="/Users/david/dms-input"
OUTPUT_DIR="/Users/david/OneDrive/Documents/DMS"

# Docker run command
docker run -p 5123:5000 \
           -v "$INPUT_DIR:/app/input" \
           -v "$OUTPUT_DIR:/app/output" \
           cyberdns/ai-document-classifier:latest