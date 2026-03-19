# Generated migration to add HR role
# This is a DATA migration - it adds initial/default data to the database

from django.db import migrations


def add_hr_role(apps, schema_editor):
    """
    Add HR role to the database
    This function is called when the migration is applied
    """
    Role = apps.get_model('users', 'Role')
    
    # Create HR role if it doesn't exist
    # get_or_create ensures we don't duplicate if migration is run multiple times
    Role.objects.get_or_create(
        role_name='HR',
        defaults={
            'description': 'Human Resources - Can manage employees, payroll, attendance, and HR-related tasks',
            'is_active': True
        }
    )
    
    # You can add more roles here if needed
    # Example:
    # Role.objects.get_or_create(
    #     role_name='Manager',
    #     defaults={
    #         'description': 'Manager role with elevated privileges',
    #         'is_active': True
    #     }
    # )


def remove_hr_role(apps, schema_editor):
    """
    Remove HR role from the database
    This function is called if the migration is rolled back
    """
    Role = apps.get_model('users', 'Role')
    Role.objects.filter(role_name='HR').delete()


class Migration(migrations.Migration):

    dependencies = [
        # This migration depends on the previous migration
        ('users', '0018_position_staff_positionlink'),
    ]

    operations = [
        # Run the function to add HR role
        migrations.RunPython(add_hr_role, remove_hr_role),
    ]

