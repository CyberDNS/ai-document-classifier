#!/bin/bash

sudo apt-get update
sudo apt-get install -y tesseract-ocr
sudo apt-get install -y imagemagick
sudo apt-get install -y keyutils
sudo apt-get install -y cifs-utils

pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt 

# Load environment variables from .env file
set -a
. ./.env
set +a

# Debugging: Print environment variables
echo "SMB_USERNAME: $SMB_USERNAME"
echo "SMB_SERVER: $SMB_SERVER"
echo "SMB_MOUNTPOINT: $SMB_MOUNTPOINT"
echo "DATA_PATH: $DATA_PATH"

# Create data path
sudo mkdir -p "$DATA_PATH"
sudo chown -R $USER:$(id -gn) "$DATA_PATH"


# Remove trailing slash from SMB_SERVER (if present)
SMB_SERVER=${SMB_SERVER%/}

# Create mount point
sudo mkdir -p "$SMB_MOUNTPOINT"

# Mount SMB share (single-line command)
sudo mount -t cifs "$SMB_SERVER" "$SMB_MOUNTPOINT" -o "username=$SMB_USERNAME,password=$SMB_PASSWORD,uid=$(id -u),gid=$(id -g)"

# Check if mount succeeded
if mount | grep -q "$SMB_MOUNTPOINT"; then
  echo "SMB share mounted successfully!"
else
  echo "Mount failed. Check logs above."
  exit 1
fi
