from django.core.management.base import BaseCommand
from django.conf import settings
from market.models import Category, Market
import json
import os
import shutil
from pathlib import Path

class Command(BaseCommand):
    help = 'Complete market data setup - loads fixtures and copies images automatically'

    def add_arguments(self, parser):
        parser.add_argument('--fixtures-dir', type=str, default='fixtures', 
                          help='Directory containing JSON files (default: fixtures)')
        parser.add_argument('--images-source', type=str, 
                          help='Source directory containing market images (optional)')
        parser.add_argument('--skip-clear', action='store_true',
                          help='Skip clearing existing data')

    def handle(self, *args, **options):
        fixtures_dir = options.get('fixtures_dir')
        images_source = options.get('images_source')
        skip_clear = options.get('skip_clear')
        
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('MARKETLENS MARKET DATA SETUP'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        # Step 1: Setup directories
        self.setup_directories()
        
        # Step 2: Clear existing data (if not skipped)
        if not skip_clear:
            self.clear_existing_data()
        
        # Step 3: Load categories
        self.load_categories(fixtures_dir)
        
        # Step 4: Load markets
        self.load_markets(fixtures_dir)
        
        # Step 5: Copy and assign market images
        self.setup_market_images(images_source)
        
        # Step 6: Show final summary
        self.show_summary()
    
    def setup_directories(self):
        """Create all necessary directories"""
        self.stdout.write(self.style.WARNING('\n📁 Setting up directories...'))
        
        # Create static images directory
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'market_covers')
        os.makedirs(static_dir, exist_ok=True)
        self.stdout.write(f"  ✓ Static images directory: {static_dir}")
        
        # Create media markets directory
        media_dir = os.path.join(settings.MEDIA_ROOT, 'markets')
        os.makedirs(media_dir, exist_ok=True)
        self.stdout.write(f"  ✓ Media markets directory: {media_dir}")
        
        return static_dir, media_dir
    
    def clear_existing_data(self):
        """Clear all existing categories and markets"""
        self.stdout.write(self.style.WARNING('\n🗑️  Clearing existing data...'))
        
        # Delete in correct order to avoid foreign key constraints
        try:
            from vendor.models import VendorProduct
            deleted_count = VendorProduct.objects.all().delete()[0]
            self.stdout.write(f"  ✓ Deleted {deleted_count} vendor products")
        except (ImportError, Exception) as e:
            self.stdout.write(f"  ⚠️  Could not delete vendor products: {e}")
        
        market_count = Market.objects.count()
        Market.objects.all().delete()
        self.stdout.write(f"  ✓ Deleted {market_count} markets")
        
        category_count = Category.objects.count()
        Category.objects.all().delete()
        self.stdout.write(f"  ✓ Deleted {category_count} categories")
        
        self.stdout.write(self.style.SUCCESS('  ✓ Existing data cleared successfully'))
    
    def load_categories(self, fixtures_dir):
        """Load categories from JSON fixture"""
        self.stdout.write(self.style.WARNING('\n📦 Loading categories...'))
        
        # Try multiple possible locations for the fixture file
        possible_paths = [
            os.path.join(settings.BASE_DIR, fixtures_dir, 'categories.json'),
            os.path.join(fixtures_dir, 'categories.json'),
            os.path.join(settings.BASE_DIR, 'market_prices', fixtures_dir, 'categories.json'),
        ]
        
        categories_file = None
        for path in possible_paths:
            if os.path.exists(path):
                categories_file = path
                self.stdout.write(f"  ✓ Found categories file: {path}")
                break
        
        if not categories_file:
            self.stdout.write(self.style.ERROR('  ❌ Categories file not found!'))
            self.stdout.write(self.style.WARNING('     Looked in:'))
            for path in possible_paths:
                self.stdout.write(f'       - {path}')
            return
        
        with open(categories_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categories_created = 0
        for item in data:
            if item['model'] == 'market.category':
                category, created = Category.objects.get_or_create(
                    name=item['fields']['name'],
                    defaults={
                        'slug': item['fields'].get('slug', ''),
                        'description': item['fields'].get('description', ''),
                        'icon': item['fields'].get('icon', 'bi-tag'),
                    }
                )
                if created:
                    categories_created += 1
                    self.stdout.write(f"    + {item['fields']['name']}")
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Successfully loaded {categories_created} categories')
        )
    
    def load_markets(self, fixtures_dir):
        """Load markets from JSON fixture"""
        self.stdout.write(self.style.WARNING('\n🏪 Loading markets...'))
        
        # Try multiple possible locations for the fixture file
        possible_paths = [
            os.path.join(settings.BASE_DIR, fixtures_dir, 'markets.json'),
            os.path.join(fixtures_dir, 'markets.json'),
            os.path.join(settings.BASE_DIR, 'market_prices', fixtures_dir, 'markets.json'),
        ]
        
        markets_file = None
        for path in possible_paths:
            if os.path.exists(path):
                markets_file = path
                self.stdout.write(f"  ✓ Found markets file: {path}")
                break
        
        if not markets_file:
            self.stdout.write(self.style.ERROR('  ❌ Markets file not found!'))
            return
        
        with open(markets_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        markets_created = 0
        for item in data:
            if item['model'] == 'market.market':
                market, created = Market.objects.get_or_create(
                    name=item['fields']['name'],
                    defaults={
                        'slug': item['fields'].get('slug', ''),
                        'location': item['fields'].get('location', ''),
                        'description': item['fields'].get('description', ''),
                        'address': item['fields'].get('address', ''),
                        'opening_hours': item['fields'].get('opening_hours', ''),
                        'contact_number': item['fields'].get('contact_number', ''),
                        'is_active': item['fields'].get('is_active', True),
                    }
                )
                if created:
                    markets_created += 1
                    self.stdout.write(f"    + {item['fields']['name']}")
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Successfully loaded {markets_created} markets')
        )
    
    def setup_market_images(self, images_source=None):
        """Find, copy, and assign market images"""
        self.stdout.write(self.style.WARNING('\n🖼️  Setting up market images...'))
        
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'market_covers')
        media_dir = os.path.join(settings.MEDIA_ROOT, 'markets')
        
        # If images_source is provided, copy images from there to static directory
        if images_source and os.path.exists(images_source):
            self.stdout.write(f"  📂 Copying images from: {images_source}")
            for file in os.listdir(images_source):
                if file.endswith('.png'):
                    src = os.path.join(images_source, file)
                    dst = os.path.join(static_dir, file)
                    shutil.copy2(src, dst)
                    self.stdout.write(f"    ✓ Copied: {file}")
        
        # Check what images we have in static directory
        if not os.path.exists(static_dir):
            self.stdout.write(self.style.ERROR(f'  ❌ Static directory not found: {static_dir}'))
            os.makedirs(static_dir, exist_ok=True)
            self.stdout.write(f'  ✓ Created directory: {static_dir}')
        
        available_images = []
        try:
            available_images = [f for f in os.listdir(static_dir) if f.endswith('.png')]
            self.stdout.write(f"  📸 Available images: {len(available_images)} found")
            for img in available_images:
                self.stdout.write(f"    - {img}")
        except OSError as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error reading directory: {e}'))
        
        # Map markets to expected image filenames
        market_images = {
            'Ikotun Market': 'ikotun-market.png',
            'Egbeda Market': 'egbeda-market.png',
            'Igando Market': 'igando-market.png',
            'LASU Market': 'lasu-market.png',
            'Iyana Ipaja Market': 'iyana-ipaja-market.png',
            'Shasha Market': 'shasha-market.png',
            'Baruwa Market': 'baruwa-market.png',
            'Meiran Market': 'meiran-market.png',
            'Oke Odo Market': 'oke-odo-market.png',
            'Alimosho Central Market': 'alimosho-central-market.png',
        }
        
        images_copied = 0
        images_missing = []
        
        for market_name, image_filename in market_images.items():
            try:
                market = Market.objects.get(name=market_name)
                source_path = os.path.join(static_dir, image_filename)
                dest_path = os.path.join(media_dir, image_filename)
                
                if os.path.exists(source_path):
                    # Copy the file to media directory
                    shutil.copy2(source_path, dest_path)
                    
                    # Update market model with the image path (relative to MEDIA_ROOT)
                    market.cover_image = f'markets/{image_filename}'
                    market.save()
                    
                    images_copied += 1
                    self.stdout.write(f"  ✓ Assigned image to: {market_name}")
                else:
                    images_missing.append(market_name)
                    
            except Market.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Market not found: {market_name}")
                )
        
        if images_copied > 0:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Successfully assigned {images_copied} market images')
            )
        
        if images_missing:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Missing images for: {", ".join(images_missing)}')
            )
            self.stdout.write(
                self.style.WARNING(f'     Please add .png images to: {static_dir}')
            )
    
    def show_summary(self):
        """Display final summary"""
        categories_count = Category.objects.count()
        markets_count = Market.objects.count()
        markets_with_images = Market.objects.exclude(cover_image='').count()
        
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✅ SETUP COMPLETE - FINAL SUMMARY'))
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(f'  📦 Categories: {categories_count}')
        self.stdout.write(f'  🏪 Markets: {markets_count}')
        self.stdout.write(f'  🖼️  Markets with images: {markets_with_images}')
        
        if markets_with_images < markets_count:
            self.stdout.write(self.style.WARNING('\n⚠️  Next steps:'))
            self.stdout.write(f'   1. Add missing .png images to: static/images/market_covers/')
            self.stdout.write(f'   2. Run: python manage.py setup_market_data --skip-clear')
        else:
            self.stdout.write(self.style.SUCCESS('\n✨ All markets have images! Ready to go!'))
        
        self.stdout.write(self.style.WARNING('='*60 + '\n'))