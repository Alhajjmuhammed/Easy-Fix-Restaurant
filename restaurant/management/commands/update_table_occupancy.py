from django.core.management.base import BaseCommand
from django.db import transaction
from restaurant.models import TableInfo
from orders.models import Order


class Command(BaseCommand):
    help = 'Update table occupancy based on active orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        updated_count = 0
        
        with transaction.atomic():
            for table in TableInfo.objects.all():
                # Check if table should be occupied
                has_active_orders = table.get_active_orders().exists()
                should_be_occupied = has_active_orders
                current_available = table.is_available
                
                if should_be_occupied and current_available:
                    # Table should be occupied but is marked as available
                    active_order = table.get_occupying_order()
                    self.stdout.write(
                        f"Table {table.tbl_no} ({table.owner.restaurant_name}) should be OCCUPIED by Order #{active_order.order_number if active_order else 'Unknown'}"
                    )
                    if not dry_run:
                        table.is_available = False
                        table.save()
                        updated_count += 1
                        
                elif not should_be_occupied and not current_available:
                    # Table should be available but is marked as occupied
                    self.stdout.write(
                        f"Table {table.tbl_no} ({table.owner.restaurant_name}) should be AVAILABLE (no active orders)"
                    )
                    if not dry_run:
                        table.is_available = True
                        table.save()
                        updated_count += 1
                        
                else:
                    # Table status is correct
                    status = "OCCUPIED" if not current_available else "AVAILABLE"
                    self.stdout.write(
                        f"Table {table.tbl_no} ({table.owner.restaurant_name}) is correctly {status}"
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would update {updated_count} tables')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} tables')
            )