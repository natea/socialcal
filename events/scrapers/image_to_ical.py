import sys
import json
import base64
import os
from openai import OpenAI

# OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Schema
schema = {
    "event_title": {
        "type": "string"
    },
    "event_date": {
        "type": "string",
        "description": "YYYY-MM-DD"
    },
    "description": {
        "type": "string"
    },
    "start_time": {
        "type": "string",
        "description": "HH:MM 24h"
    },
    "end_time": {
        "type": "string",
        "description": "HH:MM 24h"
    },
    "venue": {
        "type": "string"
    }
}

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string

def create_messages(schema, encoded_image):
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    },
                }
            ],
        },
        {
            "role": "user",
            "content": f"""
Given this schema:
{json.dumps(schema, indent=2)}
Please extract an event from the uploaded image, and write out the event in iCalendar format, for example:
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Organization//Your Product//EN
BEGIN:VEVENT
UID:20240601T100000Z-1@yourdomain.com
DTSTAMP:20231001T000000Z
DTSTART;TZID=America/Los_Angeles:20240601T100000
DTEND;TZID=America/Los_Angeles:20240601T210000
SUMMARY:World Music & Dance Day
DESCRIPTION:Occidental Center for the Arts Presents the Second Annual World Music & Dance Day.\nWatch • Play • Learn • Enjoy\n
END:VEVENT
END:VCALENDAR
Assume the timezone is America/New_York.
Assume 2025 year if the year is not present in the image.
Be sure to provide a complete iCalendar event, from BEGIN:VCALENDAR to END:VCALENDAR.
"""
        }
    ]

def main(image_path):
    # Encode image to base64
    encoded_image = encode_image_to_base64(image_path)
    
    # Create messages
    messages = create_messages(schema, encoded_image)
    
    # Send request to OpenAI API
    response = client.chat.completions.create(model="gpt-4o-mini",
    messages=messages,
    max_tokens=4096)
    
    print(response.choices[0].message.content.strip())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_event.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    main(image_path)