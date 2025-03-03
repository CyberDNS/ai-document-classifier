# Use a base image with Python pre-installed
FROM python:3.13-bullseye

# Install dependencies for SMB mounting and other tools
RUN apt-get update && apt-get install -y \
    cifs-utils \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for SMB share configuration
ENV SMB_SHARE_PATH=/mnt/smb_scans
ENV SMB_USER=your_smb_user
ENV SMB_PASSWORD=your_smb_password
ENV SMB_DOMAIN=your_smb_domain

# Create the mount point directory
RUN mkdir -p ${SMB_SHARE_PATH}

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./src /app
WORKDIR /app

# Default command (can be overridden in production)
CMD ["python", "main.py"]