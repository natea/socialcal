# Event Scraper Solution

This directory contains a generic solution for extracting events from various event listing websites. The solution is designed to be flexible and work across multiple event platforms without site-specific code.

## Files

- `event_extractor.py` - The core extractor that parses HTML event listings from any site
- `standalone_scraper.py` - A standalone script that runs the extractor without Django integration
- `integration.py` - An integration script that connects the extractor with the Django SiteScraper model
- `site_scraper.py` - Contains functions for schema generation and running with crawl4ai

## Usage

### Standalone Usage

To use the standalone script:

```bash
# Run with a specific URL
python standalone_scraper.py "https://example.com/events/"

# Custom output file
python standalone_scraper.py "https://example.com/events/" -o my_events.json
```

The extracted events will be saved to a JSON file (`extracted_events.json` by default).

## Features

The generic event extractor includes:

1. **Robust Title Extraction**: Uses multiple selectors to correctly extract event titles from various sites.
2. **Enhanced Date Parsing**: Implements sophisticated date extraction that:
   - Filters out promotional text ("Almost full", "Going fast", etc.)
   - Prioritizes structured date formats
   - Cleans up date text to remove artifacts
   - Extracts start and end times when available

3. **Flexible Location Parsing**: Uses multiple strategies to extract venue information.
4. **URL and Image Extraction**: Correctly pulls event URLs and promotional images.

## Implementation Details

The extractor uses several techniques to achieve reliable extraction:

1. **Multiple Selector Strategies**: Tries multiple CSS selectors to find event cards and their components.
2. **Pattern Matching**: Uses regular expressions to identify and extract date and time information.
3. **Priority-Based Parsing**: Assigns priorities to different date formats to ensure the most informative date is selected.
4. **Text Cleaning**: Implements extensive cleaning to remove non-date text and promotional messages.

## Schema Structure

The schema format for the crawl4ai extractor is now properly structured with both a 'fields' list for the extraction strategy and flattened properties for run_css_schema. This ensures compatibility with different components of the crawler system.

## Integration

This extractor can be used:

1. Standalone for quick event extraction
2. Integrated with the Django SiteScraper model (requires configuration)

## Results

The extractor successfully extracts:

- Event titles
- Formatted dates
- Start and end times
- Venue locations
- Event URLs and image URLs

## Troubleshooting

If extraction issues occur:

1. Check if the page structure has changed
2. Update the CSS selectors in the extractor
3. Examine the debug logs for more information
4. Try the standalone script to test extraction without Django dependencies 