import requests
from django.conf import settings

url_to_scrape = "https://en.wikipedia.org/wiki/Alexander_the_Great" # Here put the url that you want to scrape

def start_olostep(url):
    querystring = {
        "url_to_scrape": url_to_scrape,
       # optional parameters.
       # If you want to change them, uncomment and see the available options at:
       # https://docs.olostep.com/api-reference/start-agent

       # "timeout": 40,
       # "waitBeforeScraping": 1,
       # "expandMarkdown": True,
       # "expandHtml": False,
       # "saveHtml": True,
       # "saveMarkdown": True,
       # "removeImages": True,
       # "fastLane": False,
       # "removeCSSselectors": 'default',
       # "htmlTransformer": 'none'
    }

    headers = {"Authorization": "Bearer " + settings.OLOSTEP_API_KEY}

    print("Starting Olostep...")
    response = requests.request(
                    "GET",
                    "https://agent.olostep.com/olostep-p2p-incomingAPI", # API endpoint
                    headers=headers,
                    params=querystring
                )
    print(response.text)
    # response is an object that has the following structure
    # {
    #    "defaultDatasetId": "defaultDatasetId_mngjljq1qc",
    #    "html_content": "",
    #    "markdown_content": " Alexander the Great - Wikipedia...",
    #    "text_content": "",
    #    "usedProvidedNodeCountry": True
    #   }

start_olostep(url_to_scrape)
