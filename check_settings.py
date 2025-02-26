#!/usr/bin/env python
"""
Simple script to verify Django settings are loaded correctly.
Run this on your Render.com environment to debug settings issues.
"""
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings')

# Initialize Django
django.setup()

# Import settings after Django is initialized
from django.conf import settings

# Print key settings for debugging
print("=" * 50)
print("Django Settings Verification")
print("=" * 50)
print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"'www.socialcal.io' in ALLOWED_HOSTS: {'www.socialcal.io' in settings.ALLOWED_HOSTS}")
print(f"Environment Variables:")
print(f"  RENDER: {os.environ.get('RENDER', 'Not set')}")
print(f"  DEBUG: {os.environ.get('DEBUG', 'Not set')}")
print(f"  ADDITIONAL_ALLOWED_HOSTS: {os.environ.get('ADDITIONAL_ALLOWED_HOSTS', 'Not set')}")
print("=" * 50) 