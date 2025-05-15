#!/bin/bash

# Run migrations
python manage.py migrate

# Create superuser
python manage.py create_superuser

# Collect static files
python manage.py collectstatic --noinput
