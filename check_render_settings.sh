#!/bin/bash
# Script to check Django settings on Render.com

# Activate the virtual environment
source /opt/venv/bin/activate

# Run the settings check script
python check_settings.py

# Exit with success
exit 0 