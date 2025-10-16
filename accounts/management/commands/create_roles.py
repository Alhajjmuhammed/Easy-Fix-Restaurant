from django.core.management.base import BaseCommand
from accounts.models import Role

class Command(BaseCommand):
    help = 'Creates all required roles if they do not exist'

    def handle(self, *args, **options):
        """Create all roles defined in Role.ROLE_CHOICES"""
        
        self.stdout.write(self.style.WARNING('Checking and creating roles...'))
        
        # Get all role choices from the model
        role_choices = Role.ROLE_CHOICES
        
        created_count = 0
        existing_count = 0
        
        for role_name, role_display in role_choices:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': f'{role_display} role for restaurant management system'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created role: {role_name} ({role_display})')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  Role already exists: {role_name} ({role_display})')
                )
                existing_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  - Roles created: {created_count}')
        self.stdout.write(f'  - Roles existing: {existing_count}')
        self.stdout.write(f'  - Total roles: {created_count + existing_count}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ All roles are now in the database!'))
