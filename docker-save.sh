#!/bin/bash

# Get the current date for the filename
DATE=$(date +%Y%m%d_%H%M%S)
IMAGE_NAME="enbot"
OUTPUT_FILE="enbot_${DATE}.tar"

# Save the Docker image to a tar file
echo "Saving Docker image ${IMAGE_NAME} to tar file..."
docker save ${IMAGE_NAME} > "${OUTPUT_FILE}"

echo "Done! Image saved to ${OUTPUT_FILE}"
