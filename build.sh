#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations
# Use --run-syncdb to create tables for apps without migrations
python manage.py migrate --noinput --run-syncdb
