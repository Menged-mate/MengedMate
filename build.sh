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

# Create superuser
echo "Creating admin superuser..."
python manage.py create_admin_user --email admin@evmeri.com --password admin123

# Create Ethiopian charging stations
echo "Setting up Ethiopian charging stations..."
python manage.py populate_ethiopian_stations

echo "Django setup completed successfully!"
echo "✅ Ethiopian charging stations are ready!"
