#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting Django setup process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Check for Django errors
echo "Checking for Django errors..."
python manage.py check

# Apply migrations
echo "Applying migrations..."
# Use --run-syncdb to create tables for apps without migrations
python manage.py migrate --run-syncdb

echo "Django setup completed successfully!"
