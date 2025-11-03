from django.core.management.base import BaseCommand
from workshops.models import MasterIndicator
import pandas as pd

class Command(BaseCommand):
    help = "Import indicators from Excel into MasterIndicator model"

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        file_path = options['excel_file']
        self.stdout.write(self.style.SUCCESS(f"Reading Excel: {file_path}"))

        df = pd.read_excel(file_path, sheet_name='indicators_Original')
        df = df.dropna(subset=['INDICATOR'])

        count = 0
        for _, row in df.iterrows():
            MasterIndicator.objects.create(
                category=row.get('CATEGORY', ''),
                criterion=row.get('CRITERION', ''),
                name=row.get('INDICATOR', ''),
                description=row.get('DESCRIPTION', ''),
                unit=row.get('UNIT OF MEASURE', '')
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} indicators successfully."))
