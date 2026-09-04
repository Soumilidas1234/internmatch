import csv
import os
import sys

from app import app, db
from models import Internship

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "internships.csv")


def import_internships(replace=False):
    """Load fictional sample internships from data/internships.csv into SQLite."""
    if not os.path.exists(CSV_PATH):
        print("Could not find data/internships.csv")
        return 0, 0

    with app.app_context():
        if replace:
            Internship.query.delete()
            db.session.commit()
            print("Cleared existing internships.")

        imported = 0
        skipped = 0

        with open(CSV_PATH, newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                company = (row.get("company") or "").strip()
                title = (row.get("title") or "").strip()
                if not company or not title:
                    skipped += 1
                    continue

                already_there = Internship.query.filter_by(
                    company=company,
                    title=title,
                ).first()
                if already_there:
                    skipped += 1
                    continue

                internship = Internship(
                    company=company,
                    title=title,
                    description=(row.get("description") or "").strip(),
                    required_skills=(row.get("required_skills") or "").strip(),
                    location=(row.get("location") or "").strip(),
                    work_mode=(row.get("work_mode") or "").strip(),
                    duration=(row.get("duration") or "").strip(),
                    stipend=(row.get("stipend") or "").strip(),
                )
                db.session.add(internship)
                imported += 1

        db.session.commit()
        print(f"Imported {imported} internships.")
        print(f"Skipped {skipped} rows.")
        return imported, skipped


if __name__ == "__main__":
    replace = "--replace" in sys.argv
    import_internships(replace=replace)
