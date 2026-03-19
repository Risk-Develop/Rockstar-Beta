"""
Management command to change the owner password.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.hashers import make_password
import re
import os


class Command(BaseCommand):
    help = 'Change the owner login password'

    def add_arguments(self, parser):
        parser.add_argument(
            'password',
            type=str,
            help='The new password for owner login',
        )
        parser.add_argument(
            '--update-settings',
            action='store_true',
            help='Automatically update settings.py with the new hash',
        )

    def handle(self, *args, **options):
        password = options['password']
        update_settings = options['update_settings']

        # Generate the hash
        hashed = make_password(password)
        
        print(f'\nPassword: {password}')
        print(f'Hash: {hashed}\n')

        if update_settings:
            # Try multiple paths to find settings.py
            possible_paths = [
                # If running from company_system folder
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sub_company_system', 'settings.py'),
                # If running from Rockstar-Beta folder
                os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'company_system', 'sub_company_system', 'settings.py'),
                # Try absolute path
                r'C:\Users\DAVID\Documents\GitHub\Rockstar-Beta\company_system\sub_company_system\settings.py',
            ]
            
            settings_path = None
            for path in possible_paths:
                path = os.path.normpath(path)
                if os.path.exists(path):
                    settings_path = path
                    break
            
            if settings_path:
                try:
                    with open(settings_path, 'r') as f:
                        content = f.read()
                    
                    # Find and replace the OWNER_PASSWORD_HASH line
                    pattern = r"(OWNER_PASSWORD_HASH\s*=\s*os\.environ\.get\('OWNER_PASSWORD_HASH',\s*')[^']+(')"
                    replacement = f"OWNER_PASSWORD_HASH = os.environ.get('OWNER_PASSWORD_HASH', '{hashed}'"
                    
                    new_content = re.sub(pattern, replacement, content)
                    
                    if new_content != content:
                        with open(settings_path, 'w') as f:
                            f.write(new_content)
                        print('[OK] Updated settings.py with new password hash!')
                    else:
                        print('[ERROR] Could not find OWNER_PASSWORD_HASH pattern in settings.py')
                        
                except Exception as e:
                    print(f'[ERROR] Could not update settings.py: {e}')
            else:
                print('[ERROR] Could not find settings.py')
                print('Please manually update the hash in settings.py')
        else:
            print('To update the password automatically, run with --update-settings flag:')
            print(f'    python manage.py change_owner_password {password} --update-settings\n')

        print('Done!')

