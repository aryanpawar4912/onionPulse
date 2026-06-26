#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip and install packages under memory constraints
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir --no-compile

# Ensure necessary application static directories exist before running collectstatic
mkdir -p custom_admin/static
mkdir -p static
mkdir -p staticfiles

# Gather static layout configurations for Whitenoise
python manage.py collectstatic --no-input

# Migrate tables to Render PostgreSQL
python manage.py migrate

# CREATE SUPERUSER AUTOMATICALLY WITHOUT INTERACTIVE SHELL
# The "|| true" ensures the build won't crash if the user already exists
python manage.py createsuperuser --no-input || true