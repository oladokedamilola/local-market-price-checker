from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.price_alert_service import PriceAlertService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check price alerts and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=str,
            choices=['instant', 'daily', 'weekly', 'all'],
            default='all',
            help='Check alerts with specific frequency (default: all)'
        )
        parser.add_argument(
            '--send-digest',
            action='store_true',
            help='Send daily/weekly digest emails'
        )
        parser.add_argument(
            '--cleanup',
            type=int,
            nargs='?',
            const=30,
            help='Clean up alerts older than specified days (default: 30)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting price alert check...'))
        
        start_time = timezone.now()
        
        # Map frequency parameter
        frequency_map = {
            'instant': 'instant',
            'daily': 'daily',
            'weekly': 'weekly',
            'all': None
        }
        frequency = frequency_map.get(options['frequency'])
        
        # Check alerts
        try:
            triggered_count = PriceAlertService.check_all_alerts(frequency)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Checked alerts. Triggered: {triggered_count}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error checking alerts: {str(e)}')
            )
            logger.error(f"Price alert check failed: {str(e)}", exc_info=True)
        
        # Send digest if requested
        if options['send_digest']:
            try:
                # Determine which digest to send based on time
                # This is a simple example - you might want more sophisticated logic
                hour = timezone.now().hour
                
                if hour == 8:  # 8 AM - send daily digest
                    daily_count = PriceAlertService.send_daily_digest()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Daily digest sent to {daily_count} users')
                    )
                elif hour == 9 and timezone.now().weekday() == 0:  # 9 AM on Monday - send weekly digest
                    weekly_count = PriceAlertService.send_weekly_digest()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Weekly digest sent to {weekly_count} users')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error sending digest: {str(e)}')
                )
                logger.error(f"Digest sending failed: {str(e)}", exc_info=True)
        
        # Cleanup old alerts
        if options['cleanup']:
            try:
                cleaned = PriceAlertService.cleanup_old_alerts(options['cleanup'])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Cleaned up {cleaned} old alerts')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error cleaning up alerts: {str(e)}')
                )
        
        duration = (timezone.now() - start_time).total_seconds()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Price alert check completed in {duration:.2f} seconds')
        )