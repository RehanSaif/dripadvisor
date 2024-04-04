import logging
from flask import current_app, jsonify
import json
import requests
import openai
from openai import OpenAI

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
        logging.info(type(message_body))
        response = generate_response(message_body)
        data = get_text_message_input(wa_id, response)
        send_message(data)

    elif 'image' in message:
        image_id = message["image"]["id"]
        url, mime_type = retrieve_image_url(image_id)
        image_data = fetch_image(url)
        
        encoded_image = encode_image_to_base64(image_data)
        response_dict = call_gpt_vision(encoded_image)
        response_content = response_dict['choices'][0]['message']['content']
        item_recommendation = response_content.replace(' ', '%20')
        response_url = 'https://www.google.com/search?tbm=shop&q={}'.format(item_recommendation)
        logging.info(response_url)
        
        data = get_text_message_input(wa_id, response_url)
        send_message(data)
        

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

def ask_openai_vision(api_key, encoded_image, question, model='gpt-4.0-vision-preview', image_type='image/jpeg'):
    """
    Sends a request to OpenAI's Vision API with an encoded image and a question about the image.

    :param api_key: OpenAI API key for authentication.
    :param encoded_image: Base64 encoded string of the image.
    :param question: Question to ask about the image.
    :param model: The model version of the OpenAI Vision API to use.
    :param image_type: The MIME type of the image (e.g., "image/jpeg", "image/png").
    :return: The API response as a JSON object.
    """

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
    "model": "gpt-4-vision-preview",
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": question
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encoded_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

def call_gpt_vision(encoded_image, openai_api_key=OPENAI_API_KEY):
    prompt = "Assume the role of a world-class fashion stylist with an expert eye for style, trends, and coordination. Analyze the outfit worn by the individual in the uploaded image. Consider all aspects of the ensemble, including color schemes, fabric types, the occasion the outfit might be suited for, gender, and current fashion trends. Based on your analysis, recommend an item that would complement and enhance this outfit. Your suggestion should not only align with the individual's existing style but also elevate the overall look. The output should just be the item without articles."
    logging.info("Call GPT vision")
    try:
        response = ask_openai_vision(openai_api_key, encoded_image, question=prompt)
        logging.info(response)
        logging.info('Call success')
        return response  # Inspect the full response structure to extract the answer
    except Exception as e:
        return f"An error occurred: {e}"

def call_dalle(image_prompt):
    client = OpenAI()
    response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
        )

    image_url = response.data[0].url
    return(image_url)

    

