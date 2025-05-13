#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles
mkdir -p templates

# Check if templates directory exists
if [ ! -d "templates" ]; then
  echo "Error: templates directory could not be created"
  exit 1
fi

# Run the copy_templates.py script to ensure templates are available
echo "Ensuring template files are available..."
python copy_templates.py

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Check for Django errors
echo "Checking for Django errors..."
python manage.py check

# Apply migrations
echo "Applying migrations..."
# Use --run-syncdb to create tables for apps without migrations
python manage.py migrate --noinput --run-syncdb

echo "Build completed successfully!"
