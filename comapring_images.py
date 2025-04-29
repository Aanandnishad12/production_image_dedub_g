import json
import requests
import os
from dotenv import load_dotenv

load_dotenv() 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def two_image_comparision(image_name1, image_name2):
    API_KEY = GOOGLE_API_KEY
    FILES = [image_name1, image_name2]
    MIME_TYPES = ["image/png", "image/jpeg", "image/jpg",
                  "image/gif"]  # Adjust if necessary, e.g., ["image/jpeg", "image/png"]

    file_uris = []

    for i, file_path in enumerate(FILES):
        with open(file_path, "rb") as file:
            num_bytes = len(file.read())
            file.seek(0)

            headers = {
                "X-Goog-Upload-Command": "start, upload, finalize",
                "X-Goog-Upload-Header-Content-Length": str(num_bytes),
                "X-Goog-Upload-Header-Content-Type": MIME_TYPES[i],
            }

            upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={API_KEY}"
            files = {"file": (file_path, file, MIME_TYPES[i])}

            response = requests.post(upload_url, headers=headers, files=files)

            if response.status_code == 200:
                file_uri = response.json().get("file").get("uri")
                file_uris.append(file_uri)
            else:
                print(f"Failed to upload {file_path}: {response.text}")
                return None  # Stop if upload fails

    # Construct the payload with both images
    if len(file_uris) == 2:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "fileData": {
                                "fileUri": file_uris[0],
                                "mimeType": MIME_TYPES[0]
                            }
                        },
                        {
                            "fileData": {
                                "fileUri": file_uris[1],
                                "mimeType": MIME_TYPES[1]
                            }
                        },
                        {
                            "text": """Despite visual diffence and croping and format does the text in these two images convay same thing or have same 
                            schematic meaning and 2 images are same. Only Answer 'Equivalent' or 'Not Equivalent'"""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "response_mime_type": "text/plain",
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={API_KEY}",
            headers=headers,
            data=json.dumps(payload)
        )

        # Handle the response
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to generate content: {response.text}")
            return None

    else:
        print("Failed to upload both images.")
        return None

    # Extract JSON-like data from response
    # print(response.text)
    # data = re.search(r'(\[.*\])', response.json()['candidates'][0]['content']['parts'][0]['text'], flags=re.S).group(1)
    # data = str(data).replace("null","None").replace("true","True").replace("false","False")
    # data = eval(response.text)

    # return response.text
