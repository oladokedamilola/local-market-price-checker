from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clean up notifications and fix counts'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Username to fix notifications for')
        parser.add_argument('--all', action='store_true', help='Fix all users')
        parser.add_argument('--hard-delete', action='store_true', help='Permanently delete all notifications')
        parser.add_argument('--show-counts', action='store_true', help='Show notification counts')

    def handle(self, *args, **options):
        if options['show_counts']:
            self.show_counts()
            return

        if options['hard_delete']:
            self.hard_delete_all()
            return

        if options['all']:
            users = User.objects.all()
            for user in users:
                self.fix_user_notifications(user)
        elif options['user']:
            try:
                user = User.objects.get(username=options['user'])
                self.fix_user_notifications(user)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {options["user"]} not found'))
        else:
            self.stdout.write(self.style.WARNING('Please specify --user, --all, or --show-counts'))

    def show_counts(self):
        """Show notification counts for all users"""
        self.stdout.write(self.style.SUCCESS('Notification Counts:'))
        self.stdout.write('=' * 60)
        
        total_notifications = Notification.objects.count()
        total_unread = Notification.objects.filter(is_read=False).count()
        total_archived = Notification.objects.filter(is_archived=True).count()
        
        self.stdout.write(f'Total notifications: {total_notifications}')
        self.stdout.write(f'Total unread: {total_unread}')
        self.stdout.write(f'Total archived: {total_archived}')
        self.stdout.write('-' * 40)
        
        for user in User.objects.all():
            user_notifs = Notification.objects.filter(recipient=user)
            count = user_notifs.count()
            unread = user_notifs.filter(is_read=False).count()
            archived = user_notifs.filter(is_archived=True).count()
            
            if count > 0:
                self.stdout.write(
                    f'{user.username}: {count} total, {unread} unread, {archived} archived'
                )

    def hard_delete_all(self):
        """Permanently delete all notifications"""
        count = Notification.objects.all().delete()[0]
        self.stdout.write(
            self.style.SUCCESS(f'✅ Permanently deleted {count} notifications')
        )

    def fix_user_notifications(self, user):
        """Fix notification counts for a specific user"""
        self.stdout.write(f'Processing user: {user.username}')
        
        # Get all notifications for user
        notifications = Notification.objects.filter(recipient=user)
        total = notifications.count()
        
        if total == 0:
            self.stdout.write(f'  No notifications for {user.username}')
            return
        
        # Fix any inconsistencies
        unread_count = notifications.filter(is_read=False).count()
        archived_count = notifications.filter(is_archived=True).count()
        
        self.stdout.write(f'  Before: {total} total, {unread_count} unread, {archived_count} archived')
        
        # Option 1: Archive old read notifications (older than 30 days)
        old_read = notifications.filter(
            is_read=True,
            created_at__lt=timezone.now() - timedelta(days=30)
        )
        old_read_count = old_read.count()
        old_read.update(is_archived=True)
        
        # Option 2: Delete very old archived notifications (older than 90 days)
        very_old = notifications.filter(
            is_archived=True,
            created_at__lt=timezone.now() - timedelta(days=90)
        )
        deleted_count = very_old.delete()[0]
        
        # Get new counts
        new_total = Notification.objects.filter(recipient=user).count()
        new_unread = Notification.objects.filter(recipient=user, is_read=False).count()
        new_archived = Notification.objects.filter(recipient=user, is_archived=True).count()
        
        self.stdout.write(f'  After: {new_total} total, {new_unread} unread, {new_archived} archived')
        self.stdout.write(f'  Archived {old_read_count} old read notifications')
        self.stdout.write(f'  Deleted {deleted_count} very old notifications')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Fixed notifications for {user.username}'))