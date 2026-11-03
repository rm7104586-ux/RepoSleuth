#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install production dependencies
pip install -r requirements.txt

# Collect static files into staticfiles/ for WhiteNoise
python manage.py collectstatic --no-input

# Run database migrations (creates PostgreSQL tables)
python manage.py migrate

# Seed initial sample project for instant preview
python manage.py seed_demo
