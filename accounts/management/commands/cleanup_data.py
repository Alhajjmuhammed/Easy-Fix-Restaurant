from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from accounts.models import User, Role
from django.utils import timezone


class Command(BaseCommand):
    help = 'Clean up orphaned users and fix data consistency issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes',
        )
        parser.add_argument(
            '--delete-orphaned',
            action='store_true',
            help='Delete orphaned users without owners',
        )
        parser.add_argument(
            '--assign-default-owner',
            type=str,
            help='Assign orphaned users to a specific owner username',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Starting data consistency scan...'))
        
        # Find orphaned users
        orphaned_users = User.objects.filter(
            owner__isnull=True
        ).exclude(
            role__name__in=['owner', 'administrator']
        ).exclude(
            role__isnull=True
        )
        
        self.stdout.write(f"\n📊 Data Analysis:")
        self.stdout.write(f"   Total users: {User.objects.count()}")
        self.stdout.write(f"   Owners: {User.objects.filter(role__name='owner').count()}")
        self.stdout.write(f"   Orphaned users: {orphaned_users.count()}")
        
        if orphaned_users.exists():
            self.stdout.write(f"\n⚠️  Found {orphaned_users.count()} orphaned users:")
            for user in orphaned_users:
                self.stdout.write(
                    f"   - {user.username} ({user.role.name if user.role else 'No Role'}) "
                    f"- Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}"
                )
        
        # Find users without roles
        users_without_roles = User.objects.filter(role__isnull=True)
        if users_without_roles.exists():
            self.stdout.write(f"\n⚠️  Found {users_without_roles.count()} users without roles:")
            for user in users_without_roles:
                self.stdout.write(f"   - {user.username} - Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Check for owners without restaurant names
        owners_without_restaurants = User.objects.filter(
            role__name='owner'
        ).filter(
            models.Q(restaurant_name__isnull=True) | models.Q(restaurant_name='')
        )
        if owners_without_restaurants.exists():
            self.stdout.write(f"\n⚠️  Found {owners_without_restaurants.count()} owners without restaurant names:")
            for owner in owners_without_restaurants:
                self.stdout.write(f"   - {owner.username}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN - No changes made'))
            return
        
        # Perform cleanup actions
        if options['delete_orphaned'] and orphaned_users.exists():
            self.stdout.write(f"\n🗑️  Deleting {orphaned_users.count()} orphaned users...")
            with transaction.atomic():
                deleted_count = orphaned_users.delete()[0]
                self.stdout.write(self.style.SUCCESS(f"✅ Deleted {deleted_count} orphaned users"))
        
        elif options['assign_default_owner'] and orphaned_users.exists():
            try:
                default_owner = User.objects.get(
                    username=options['assign_default_owner'],
                    role__name='owner'
                )
                self.stdout.write(f"\n👤 Assigning {orphaned_users.count()} users to owner: {default_owner.username}")
                with transaction.atomic():
                    updated_count = orphaned_users.update(owner=default_owner)
                    self.stdout.write(self.style.SUCCESS(f"✅ Assigned {updated_count} users to {default_owner.username}"))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Owner '{options['assign_default_owner']}' not found"))
        
        # Assign customer role to users without roles
        if users_without_roles.exists():
            try:
                customer_role = Role.objects.get(name='customer')
                self.stdout.write(f"\n👥 Assigning customer role to {users_without_roles.count()} users...")
                with transaction.atomic():
                    updated_count = users_without_roles.update(role=customer_role)
                    self.stdout.write(self.style.SUCCESS(f"✅ Assigned customer role to {updated_count} users"))
            except Role.DoesNotExist:
                self.stdout.write(self.style.ERROR("❌ Customer role not found. Creating it..."))
                customer_role = Role.objects.create(
                    name='customer',
                    description='Restaurant customer'
                )
                updated_count = users_without_roles.update(role=customer_role)
                self.stdout.write(self.style.SUCCESS(f"✅ Created customer role and assigned to {updated_count} users"))
        
        self.stdout.write(f"\n✨ Data cleanup completed!")
        
        # Final summary
        self.stdout.write(f"\n📊 Final Status:")
        self.stdout.write(f"   Total users: {User.objects.count()}")
        self.stdout.write(f"   Owners: {User.objects.filter(role__name='owner').count()}")
        self.stdout.write(f"   Users with owners: {User.objects.filter(owner__isnull=False).count()}")
        self.stdout.write(f"   Orphaned users: {User.objects.filter(owner__isnull=True).exclude(role__name__in=['owner', 'administrator']).count()}")