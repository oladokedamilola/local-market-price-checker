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

# ============ DJANGO DEBUGGING SECTION ============
echo "=== DJANGO DEBUG ==="
python -c "
import sys
print(f'Python executable: {sys.executable}')
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path}')

try:
    import django
    print(f'✓ Django found! Version: {django.get_version()}')
    print(f'✓ Django location: {django.__file__}')
    
    # Try to import management commands
    from django.core.management import execute_from_command_line
    print('✓ Django management imported successfully')
    
    # List all available management commands
    from django.core.management import get_commands
    commands = get_commands()
    print(f'Available commands: {list(commands.keys())}')
    
except ImportError as e:
    print(f'✗ Django import failed: {e}')
    sys.exit(1)
"

# Check if manage.py exists and is readable
echo "=== CHECKING MANAGE.PY ==="
if [ -f "manage.py" ]; then
    echo "✓ manage.py exists"
    head -n 5 manage.py
    chmod +x manage.py
else
    echo "✗ manage.py not found!"
    exit 1
fi

# Try to get help from manage.py
echo "=== TESTING MANAGE.PY ==="
python manage.py help || echo "✗ manage.py help failed"

# Set Django settings module
export DJANGO_SETTINGS_MODULE=market_prices.settings_production
echo "✓ DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

# Try collectstatic with different methods
echo "=== ATTEMPTING COLLECTSTATIC (Method 1) ==="
python manage.py collectstatic --no-input -v 3 --traceback || {
    echo "Method 1 failed, trying Method 2..."
    
    echo "=== ATTEMPTING COLLECTSTATIC (Method 2) ==="
    python -m django collectstatic --settings=market_prices.settings_production --no-input -v 3 || {
        echo "Method 2 failed, trying Method 3..."
        
        echo "=== ATTEMPTING COLLECTSTATIC (Method 3) ==="
        DJANGO_SETTINGS_MODULE=market_prices.settings_production django-admin collectstatic --no-input -v 3 || {
            echo "✗ All collectstatic methods failed"
            
            # List installed packages for debugging
            echo "=== INSTALLED PACKAGES ==="
            pip list
            
            # Check Django installation details
            echo "=== DJANGO INSTALLATION DETAILS ==="
            python -c "
import django
print(f'Django version: {django.get_version()}')
print(f'Django path: {django.__file__}')
print(f'Django package contents:')
import os
for root, dirs, files in os.walk(os.path.dirname(django.__file__)):
    level = root.replace(os.path.dirname(django.__file__), '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for f in files[:5]:  # Show first 5 files in each directory
        print(f'{subindent}{f}')
"
            exit 1
        }
    }
}
# ============ END DEBUGGING SECTION ============

# Make migrations
echo "=== MAKING MIGRATIONS ==="
python manage.py makemigrations accounts core market notifications vendor --no-input

# Run database migrations
echo "=== RUNNING MIGRATIONS ==="
python manage.py migrate --no-input

# Create superuser if it doesn't exist (optional)
echo "=== CREATING SUPERUSER (IF NEEDED) ==="
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
    print("✓ Superuser created successfully")
else:
    print("✓ Superuser already exists")
EOF

echo "=== BUILD COMPLETED SUCCESSFULLY ==="