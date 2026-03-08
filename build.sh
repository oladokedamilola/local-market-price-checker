#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

python manage.py makemigrations accounts core market notifications vendor

# Run database migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional)
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email=os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@marketlens.com'),
        password=os.getenv('DJANGO_SUPERUSER_PASSWORD', 'changeme123')
    )
EOF