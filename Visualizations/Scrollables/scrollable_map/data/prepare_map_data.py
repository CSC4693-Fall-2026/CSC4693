"""Prepare small, browser-ready assets for the scrollable California map."""

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

MAP_DIR = Path(__file__).resolve().parent
REPO_DIR = MAP_DIR.parents[3]
STEEL_THREAD = REPO_DIR / "Steel Thread" / "for_analysis"
OUTPUT_DIR = MAP_DIR / "derived"
PUBLIC_OUTPUT_DIR = MAP_DIR.parent / "public" / "data" / "derived"
ALIASES = {
    "Cal Poly Maritime Academy": "California State University Maritime Academy",
    "Humphreys University": "Humphreys University-Stockton and Modesto Campuses",
}


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalized(value):
    return " ".join((value or "").strip().split())


def write_json(filename, rows):
    OUTPUT_DIR.mkdir(exist_ok=True)
    PUBLIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for output_dir in (OUTPUT_DIR, PUBLIC_OUTPUT_DIR):
        with (output_dir / filename).open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2)
            handle.write("\n")


def prepare_faculty_benchmark():
    """Median Cal Poly faculty base pay used as the statewide POC benchmark."""
    base_pay = []
    with (STEEL_THREAD / "calpoly_salary_data.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            value = number(row["base"])
            if value is not None and value > 0:
                base_pay.append(value)
    if not base_pay:
        raise ValueError("No positive Cal Poly faculty base-pay values were found.")
    return round(median(base_pay))


def prepare_schools(faculty_benchmark):
    earnings_by_school = defaultdict(list)
    with (STEEL_THREAD / "ca_collegescore.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["CREDDESC"] != "Bachelor's Degree":
                continue
            earnings = number(row["EARN_MDN_5YR"])
            if earnings is not None:
                earnings_by_school[normalized(row["INSTNM"])].append(earnings)

    locations = {}
    with (MAP_DIR / "CaliforniaCollegeLoc.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            longitude, latitude = number(row["LONGITUD"]), number(row["LATITUDE"])
            if longitude is not None and latitude is not None:
                locations[normalized(row["INSTNM"])] = (longitude, latitude, row["CITY"])

    schools, unmatched = [], []
    for institution, earnings in sorted(earnings_by_school.items()):
        location = locations.get(ALIASES.get(institution, institution))
        if location is None:
            unmatched.append(institution)
            continue
        longitude, latitude, city = location
        median_earnings = round(median(earnings))
        schools.append({"institution": institution, "city": city, "longitude": longitude, "latitude": latitude,
                        "medianEarnings": median_earnings, "programCount": len(earnings),
                        "facultyBenchmark": faculty_benchmark,
                        "studentMinusFacultyGap": median_earnings - faculty_benchmark})
    return schools, unmatched, len(earnings_by_school)


def prepare_calpoly_gaps():
    faculty = {}
    with (STEEL_THREAD / "calpoly_major_medians.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            value = number(row["totalpaybenefits"])
            if value is not None:
                faculty[normalized(row["Major"])] = value

    graduate_values = defaultdict(list)
    with (STEEL_THREAD / "calpoly_scorecard.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["CREDDESC"] == "Bachelor's Degree":
                value = number(row["EARN_MDN_5YR"])
                if value is not None:
                    graduate_values[normalized(row["Major"])].append(value)

    gaps = []
    for major, compensation in faculty.items():
        if major in graduate_values:
            graduate_earnings = median(graduate_values[major])
            gaps.append({"major": major, "facultyCompensation": round(compensation),
                         "graduateEarnings": round(graduate_earnings), "gap": round(compensation - graduate_earnings)})
    ordered = sorted(gaps, key=lambda row: row["gap"])
    smallest = [dict(row, comparisonGroup="Smallest or negative gaps") for row in ordered[:5]]
    largest = [dict(row, comparisonGroup="Largest faculty-over-graduate gaps")
               for row in reversed(ordered[-5:])]
    return largest + smallest


def main():
    faculty_benchmark = prepare_faculty_benchmark()
    schools, unmatched, candidates = prepare_schools(faculty_benchmark)
    gaps = prepare_calpoly_gaps()
    write_json("schools.json", schools)
    write_json("calpoly-major-gaps.json", gaps)
    write_json("prep-report.json", {"candidateInstitutions": candidates, "mappedInstitutions": len(schools),
                                      "unmatchedInstitutions": unmatched, "calPolyMajorComparisons": len(gaps),
                                      "calPolyFacultyBasePayBenchmark": faculty_benchmark})
    print(f"Wrote {len(schools)} mapped institutions and {len(gaps)} Cal Poly major comparisons.")
    if unmatched:
        print("Excluded for missing locations:", ", ".join(unmatched))


if __name__ == "__main__":
    main()
