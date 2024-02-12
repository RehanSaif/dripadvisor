import logging
from flask import current_app, jsonify
import json
import requests

# from app.services.openai_service import generate_response
import re

import base64
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Return text in uppercase
    return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    logging.info("Message Body {}".format(body))
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    if 'text' in message:
        message_body = message["text"]["body"]
        response = generate_response(message_body)
        data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
        send_message(data)

    elif 'image' in message:
        image_id = message["image"]["id"]
        url, mime_type = retrieve_image_url(image_id)
        image_data = fetch_image(url)
        
        encoded_image = encode_image_to_base64(image_data)
        answer = call_gpt_vision(encoded_image)
        logging.info(answer)
        

    # TODO: implement custom function here

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    # response = process_text_for_whatsapp(response)

    


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

def retrieve_image_url(media_id):
    url = url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}/"
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Assuming the response contains JSON data
        logging.info('Retrieved media')
        data = response.json()
        logging.info(data)
        return data.get("url"), data.get("mime_type")
    else:
        logging.info(f'Failed to fetch media. Status code: {response.status_code}, Response: {response.text}')
        return None
    
def fetch_image(image_url):
    url = image_url

    headers = {
        'Authorization': f"Bearer {current_app.config['ACCESS_TOKEN']}"
    }

    response = requests.get(url, headers=headers)
    #logging.info(response)

    if response.status_code == 200:
        
        #with open('media_file', 'wb') as f:
        #    f.write(response.content)
        logging.info("Media file downloaded successfully.")
        return response.content
    else:
        logging.info(f"Failed to download media file. Status code: {response.status_code}")
        return None

def encode_image_to_base64(image_data):
    """
    Reads an image from the specified path and encodes it to base64.

    :param image_path: Path to the image file.
    :return: Base64 encoded string of the image.
    """
    logging.info('Image encoded')
    return base64.b64encode(image_data).decode('utf-8')

def ask_openai_vision(api_key, encoded_image, question, model='gpt-4.0-vision', image_type='image/jpeg'):
    """
    Sends a request to OpenAI's Vision API with an encoded image and a question about the image.

    :param api_key: OpenAI API key for authentication.
    :param encoded_image: Base64 encoded string of the image.
    :param question: Question to ask about the image.
    :param model: The model version of the OpenAI Vision API to use.
    :param image_type: The MIME type of the image (e.g., "image/jpeg", "image/png").
    :return: The API response as a JSON object.
    """
    url = 'https://api.openai.com/v1/images/generations'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model,
        "n": 1,  # Number of generations to return
        "prompt": {
            "text": question,
            "image": {
                "data": encoded_image,
                "type": image_type  # Adjust if your image is in a different format
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

def call_gpt_vision(encoded_image, openai_api_key=OPENAI_API_KEY):
    question = "What is this image about?"  # Your question about the image
    logging.info("Call GPT vision")
    try:
        response = ask_openai_vision(openai_api_key, encoded_image, question)
        return response  # Inspect the full response structure to extract the answer
    except Exception as e:
        return f"An error occurred: {e}"
        

