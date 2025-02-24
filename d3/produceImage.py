from google.cloud import pubsub_v1  # pip install google-cloud-pubsub  ##to install
import glob  # for searching for image files
import base64
import os
import random
import json
import numpy as np  # pip install numpy    ##to install
import time

# Search the current directory for the JSON file (including the service account key) 
# to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
files = glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

# Set the project ID and topic
project_id = "project1-448716"
topic_name = "design_images"

# Set up the Pub/Sub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

# Specify the folder where images are located
image_folder = "Dataset_Occluded_Pedestrian"

# Get image files
image_files = [
    f for f in glob.glob(os.path.join(image_folder, "*.jpg")) + glob.glob(os.path.join(image_folder, "*.png"))
    if os.path.basename(f).startswith("A")
]

for image_file in image_files:
    with open(image_file, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode("utf-8")  # Convert to Base64 string

    # Create a JSON message
    message = json.dumps({"ID": os.path.basename(image_file), "Image": encoded_image})

    try:
        # Publish message
        future = publisher.publish(topic_path, message.encode("utf-8"))
        future.result()  # Ensure it was sent
        print(f"Published {image_file} successfully.")
    except Exception as e:
        print(f"Failed to publish {image_file}: {e}")