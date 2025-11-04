import pandas as pd
from django.core.management.base import BaseCommand
from workshops.models import MasterIndicator


class Command(BaseCommand):
    help = "Import indicators from CSV into MasterIndicator table (auto-filling missing categories)."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")

    def handle(self, *args, **options):
        path = options["csv_file"]
        print(f"Reading CSV: {path}")

        df = pd.read_csv(path)

        # Normalize all column names
        df.columns = [c.strip().lower() for c in df.columns]

        # Debug print to verify column detection
        print("Detected columns:", df.columns.tolist())

        # Fill down blank categories and criteria
        for col in df.columns:
            df[col] = df[col].ffill()

        count = 0
        for _, row in df.iterrows():
            category = str(row.get("category", "")).strip()
            criterion = str(row.get("criterion", "")).strip()
            name = str(row.get("indicator", "")).strip()
            description = str(row.get("description", "")).strip()
            unit = str(row.get("unit of measure", "")).strip()

            # handle if the column had trailing space in name
            if not description and "description " in df.columns:
                description = str(row.get("description ", "")).strip()

            if not name:
                continue

            MasterIndicator.objects.create(
                category=category,
                criterion=criterion,
                name=name,
                description=description,
                unit=unit,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} indicators successfully."))
