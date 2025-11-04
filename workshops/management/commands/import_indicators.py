import pandas as pd
from django.core.management.base import BaseCommand
from workshops.models import MasterIndicator

class Command(BaseCommand):
    help = "Import indicators from Excel into MasterIndicator table"

    def add_arguments(self, parser):
        parser.add_argument("excel_file", type=str, help="Path to Excel file")

    def handle(self, *args, **options):
        path = options["excel_file"]
        print(f"Reading Excel: {path}")

        df = pd.read_excel(path)

        # Fill down category and criterion columns (handles merged/blank cells)
        df['Category'] = df['Category'].ffill()
        df['Criterion'] = df['Criterion'].ffill()

        count = 0
        for _, row in df.iterrows():
            category = str(row.get('Category', '')).strip()
            name = str(row.get('Indicator name', '')).strip()
            description = str(row.get('Description', '')).strip()
            criterion = str(row.get('Criterion', '')).strip()
            unit = str(row.get('Unit of measure', '')).strip()

            if not name:
                continue  # skip empty rows

            MasterIndicator.objects.create(
                category=category,
                name=name,
                description=description,
                criterion=criterion,
                unit=unit,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} indicators successfully."))
