"""Create a California-only copy of the HD2024 college locations dataset."""

import csv
from pathlib import Path


DATA_DIR = Path(__file__).parent
INPUT_FILE = DATA_DIR / "US National Colleges Size and Locations - HD2024.csv"
OUTPUT_FILE = DATA_DIR / "California Colleges Size and Locations - HD2024.csv"


def main() -> None:
    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if "STABBR" not in (reader.fieldnames or []):
            raise ValueError(f"{INPUT_FILE.name} does not contain a STABBR column.")

        california_schools = (row for row in reader if row["STABBR"].strip().upper() == "CA")

        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as destination:
            writer = csv.DictWriter(destination, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(california_schools)

    print(f"Wrote California schools to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
