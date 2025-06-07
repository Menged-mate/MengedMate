#!/bin/bash

# Run migrations
python manage.py migrate

# Create superuser
python manage.py create_superuser

# Collect static files
python manage.py collectstatic --noinput

# Create Ethiopian charging stations
echo "Setting up Ethiopian charging stations..."
python manage.py populate_ethiopian_stations

echo "✅ Ethiopian charging stations are ready!"
