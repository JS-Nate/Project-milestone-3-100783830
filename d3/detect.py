import argparse
import json
import logging
import apache_beam as beam
import cv2
import numpy as np
from google.cloud import storage
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions


class DetectPedestriansDoFn(beam.DoFn):
    """Loads the Haar cascade model and performs pedestrian detection."""
    
    def __init__(self, model_path):
        self.model_path = model_path
        self.local_model_path = "/tmp/haarcascade_fullbody.xml"  # Temporary model path
        self.cascade = None
    
    def setup(self):
        """Downloads the Haar cascade from GCS if necessary and loads it."""
        if self.model_path.startswith("gs://"):  # Model is in Google Cloud Storage
            logging.info(f"Downloading model from {self.model_path} to {self.local_model_path}")
            try:
                self.download_from_gcs(self.model_path, self.local_model_path)
                logging.info("Model downloaded successfully.")
            except Exception as e:
                logging.error(f"Failed to download model: {e}")
                return
        else:
            self.local_model_path = self.model_path  # Use local model file
        
        # Load Haar Cascade
        self.cascade = cv2.CascadeClassifier(self.local_model_path)
        if self.cascade.empty():
            logging.error("Failed to load Haar cascade.")
            self.cascade = None
        else:
            logging.info("Haar cascade loaded successfully.")

    def download_from_gcs(self, gcs_path, local_path):
        """Downloads a file from GCS to a local path."""
        gcs_client = storage.Client()
        bucket_name, blob_name = gcs_path.replace("gs://", "").split("/", 1)
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)

    def process(self, element):
        """Processes each message, decodes the image, and performs pedestrian detection."""
        try:
            message_data = element.data if hasattr(element, "data") else element
            parsed_message = json.loads(message_data)
            image_id = parsed_message.get("ID", "Unknown")
            image_data = parsed_message.get("Image")

            if not image_data:
                logging.error(f"Missing image data for {image_id}")
                return [{"ID": image_id, "Status": "Failed - No Image Data"}]

            # Decode image
            image_np = np.frombuffer(bytes(image_data, "utf-8"), dtype=np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

            if image is None:
                logging.error(f"Failed to decode image for {image_id}")
                return [{"ID": image_id, "Status": "Failed - Image Decode Error"}]
            
            if self.cascade is None:
                return [{"ID": image_id, "Status": "Failed - Cascade Not Loaded"}]
            
            # Perform pedestrian detection
            detections = self.cascade.detectMultiScale(image, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
            detections_list = detections.tolist() if len(detections) > 0 else []

            result = {"ID": image_id, "Detections": detections_list}
            logging.info(f"Processed {image_id}: {result}")
            return [result]

        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e} - Raw data: {element}")
            return [{"ID": "Unknown", "Status": "Failed - JSON Decode Error"}]
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return [{"ID": "Unknown", "Status": "Failed - Unknown Error"}]


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input Pub/Sub topic.')
    parser.add_argument('--output', required=True, help='Output Pub/Sub topic.')
    parser.add_argument('--model', required=True, help='Path to Haar cascade model (local or GCS).')
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True

    with beam.Pipeline(options=pipeline_options) as p:
        messages = (
            p | "Read from Pub/Sub" >> beam.io.ReadFromPubSub(topic=known_args.input, with_attributes=True)
              | "Detect Pedestrians" >> beam.ParDo(DetectPedestriansDoFn(known_args.model))
        )

        (
            messages | "Convert to JSON" >> beam.Map(lambda x: json.dumps(x).encode('utf-8'))
                     | "Write to Pub/Sub" >> beam.io.WriteToPubSub(topic=known_args.output)
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
