from firecrawl import FirecrawlApp
import json
from groq import Groq
from datetime import datetime

# Initialize the clients
firecrawl = FirecrawlApp(api_key='fc-d430d76deeb444f680f93e24848ad01b')
groq = Groq(api_key="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")  # Replace with your Groq API key

def log_debug(message, data=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    if data:
        print(json.dumps(data, indent=2))
    print("-" * 80)

log_debug("Starting Berklee events scraper")

# First, get the page content
log_debug("Fetching page content...")
page_data = firecrawl.scrape_url('https://www.berklee.edu/events/performances', {
    'formats': ['markdown']
})
page_content = page_data['markdown']

# Define the fields we want to extract
fields_to_extract = [
    "event_title",
    "event_date",
    "event_time",
    "event_venue",
    "event_address",
    "event_city",
    "event_state",
    "event_zip",
    "event_country",
    "event_description",
    "event_url",
    "event_cost",
    "event_image_url"
]

log_debug("Extracting events using Groq LLama3...")
completion = groq.chat.completions.create(
    model="llama3-8b-8192",
    messages=[
        {
            "role": "system",
            "content": "You are an expert at extracting event information from web pages. Extract exactly 5 events and format them as a JSON array."
        },
        {
            "role": "user",
            "content": f"Extract the first 10 events from this Berklee performances page. For each event, extract these fields: {fields_to_extract}\n\nPage content:\n\n{page_content}"
        }
    ],
    temperature=0,
    max_tokens=2048,
    top_p=1,
    stream=False,
    stop=None,
    response_format={"type": "json_object"}
)

# Get the extracted data
events_data = json.loads(completion.choices[0].message.content)

# Print the extracted events
log_debug("Processing events...")
for i, event in enumerate(events_data['events'], 1):
    log_debug(f"Event {i}/10", event)

log_debug("Scraping completed!")
