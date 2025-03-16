# Stage 1: Build the frontend
FROM node:18 AS frontend-builder

WORKDIR /app/frontend

COPY ai-document-classifier-vuetify/package.json ./
RUN yarn install

COPY ai-document-classifier-vuetify ./
RUN yarn build

# Stage 2: Build the backend
FROM python:3.13-bookworm


# Install dependencies for SMB mounting and other tools
RUN apt-get update && apt-get install -y \
    keyutils \
    cifs-utils \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Set locale to en_US.UTF-8
RUN locale-gen en_US.UTF-8


# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./src /app
WORKDIR /app

# Copy the built frontend from the previous stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend

# Copy the startup script
COPY startup.sh /app/startup.sh

# Make the startup script executable
RUN chmod +x /app/startup.sh

# Set the entrypoint to the startup script
ENTRYPOINT ["/app/startup.sh"]

# Default command (can be overridden in production)
CMD ["python", "main.py"]