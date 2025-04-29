import os
from dotenv import load_dotenv
from google.cloud import vision

# Load environment variables from .env
load_dotenv()

# Set up credentials from .env
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def detect_text_from_binary(image_binary):
    """Detects text in an image from binary data using Google Vision API."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_binary)

    response = client.text_detection(image=image)
    texts = response.text_annotations

    if response.error.message:
        raise Exception(
            '{}\nFor more info: https://cloud.google.com/apis/design/errors'.format(response.error.message)
        )

    if texts:
        print('Detected Text:')
        print(texts[0].description)
        return texts[0].description
    else:
        print("No text detected")
        return ""
