#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "🚀 Starting build process..."

# Show Python version
echo "Python version:"
python --version

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Ensure we're in the right directory
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

# Set Python path to include current directory
export PYTHONPATH="${PYTHONPATH}:${PWD}"
export DJANGO_SETTINGS_MODULE=market_prices.settings_production

# Verify Django can be imported
echo "Verifying Django installation..."
python -c "
import django
print(f'✅ Django {django.get_version()} imported successfully')
from django.conf import settings
print('✅ Django settings module can be loaded')
"

# Create static directory if it doesn't exist
mkdir -p staticfiles

# Run collectstatic with full Python path
echo "Collecting static files..."
python -m django collectstatic --noinput -v 2

# Make migrations
echo "Making migrations..."
python manage.py makemigrations --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser
echo "Creating superuser if needed..."
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
    print('✅ Superuser created')
else:
    print('✅ Superuser already exists')
EOF

echo "✅ Build completed successfully!"