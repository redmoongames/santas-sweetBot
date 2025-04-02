#!/bin/bash

# Exit on error
set -e

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found. Create an .env file with your API keys:"
  echo "TELEGRAM_TOKEN=your_telegram_bot_token"
  echo "OPENAI_API_KEY=your_openai_api_key"
  exit 1
fi

# Define container name for easier management
CONTAINER_NAME="rea-tgbot"

# Check if container is already running and stop it
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
  echo "Stopping existing container..."
  docker stop $CONTAINER_NAME
fi

# Remove container if it exists (even if not running)
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
  echo "Removing existing container..."
  docker rm $CONTAINER_NAME
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t $CONTAINER_NAME .

# Run the container in detached mode
echo "Starting bot container..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --env-file .env \
  -v "$(pwd):/app" \
  $CONTAINER_NAME

echo "Bot is now running in the background."
echo "Use 'docker logs $CONTAINER_NAME' to view logs."
echo "Use 'docker stop $CONTAINER_NAME' to stop the bot." 