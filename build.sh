#!/usr/bin/env bash
# Exit on error
set -o errexit

# Print commands for debugging
set -x

# Show Python version
echo "Python version being used:"
python --version

# Install dependencies
pip install -r requirements.txt

# Show current directory structure (for debugging)
echo "Current directory structure:"
ls -la
echo "Static directory contents:"
ls -la static/ || echo "Static directory not found"

# Set production settings
export DJANGO_SETTINGS_MODULE=market_prices.settings_production

# Collect static files - with verbose output
python manage.py collectstatic --no-input -v 2

# Make migrations (only if needed, but better to have them committed)
python manage.py makemigrations accounts core market notifications vendor --no-input

# Run database migrations
python manage.py migrate --no-input

# Create superuser if it doesn't exist (optional)
python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email=os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@marketlens.com'),
        password=os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123')
    )
    print("Superuser created successfully")
else:
    print("Superuser already exists")
EOF

echo "Build completed successfully!"