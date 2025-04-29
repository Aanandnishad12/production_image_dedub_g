import boto3
import time
from botocore.exceptions import NoCredentialsError, ClientError
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Now load AWS credentials from env
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

def download_image(image_url):
    """Downloads a single image from S3 and returns its binary data."""

    bucket_name = 'larvolclin'

    # Initialize S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name='us-west-2'
    )

    def download_from_s3(bucket, image_key, retries=3):
        """Helper function to download an image from S3 and return binary data."""
        for attempt in range(retries):
            try:
                image_data = BytesIO()
                s3.download_fileobj(bucket, image_key, image_data)
                image_data.seek(0)
                print(f'✅ Downloaded: {image_key}')
                return image_data.read()
            except NoCredentialsError:
                print('❌ AWS credentials not available.')
                return None
            except ClientError as e:
                if attempt < retries - 1:
                    print(f'⚠️ Error downloading {image_key}. Retrying ({attempt + 1}/{retries})...')
                    time.sleep(2 ** attempt)
                else:
                    print(f'❌ Failed to download {image_key}: {e}')
                    return None

    image_key = image_url.split("/")[-1]
    return download_from_s3(bucket_name, image_key)
