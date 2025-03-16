#!/bin/bash

# Set locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Load environment variables from .env file if it exists
if [ -f ./.env ]; then
  set -a
  . ./.env
  set +a
fi

# Debugging: Print environment variables
echo "SMB_USERNAME: $SMB_USERNAME"
echo "SMB_SERVER: $SMB_SERVER"
echo "SMB_MOUNTPOINT: $SMB_MOUNTPOINT"
echo "DATA_PATH: $DATA_PATH"

# Create data path
mkdir -p "$DATA_PATH"
chown -R $USER:$(id -gn) "$DATA_PATH"

# Remove trailing slash from SMB_SERVER (if present)
SMB_SERVER=${SMB_SERVER%/}

# Create mount point
mkdir -p "$SMB_MOUNTPOINT"

# Mount SMB share (single-line command)
mount -t cifs "$SMB_SERVER" "$SMB_MOUNTPOINT" -o "username=$SMB_USERNAME,password=$SMB_PASSWORD,uid=$(id -u),gid=$(id -g),iocharset=utf8"

# Check if mount succeeded
if mount | grep -q "$SMB_MOUNTPOINT"; then
  echo "SMB share mounted successfully!"
else
  echo "Mount failed. Check logs above."
  exit 1
fi

# Start the main application
exec "$@"