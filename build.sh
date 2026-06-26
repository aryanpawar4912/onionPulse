#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip and install packages under memory constraints
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir --no-compile

# Gather static layout configurations for Whitenoise
python manage.py collectstatic --no-input

# Migrate tables to Render PostgreSQL
python manage.py migrate