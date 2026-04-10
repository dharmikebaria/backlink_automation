# management/commands/load_credentials.py
from django.core.management.base import BaseCommand
from backlinkapp.models import Credential

class Command(BaseCommand):
    help = 'Load credentials from Excel file'
    
    def handle(self, *args, **options):
        success, message = Credential.load_from_excel()
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(message))