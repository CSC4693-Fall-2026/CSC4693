
from pathlib import Path
import polars as pl

ROOT = Path(__file__).resolve().parents[4]

STUDENT_PATH = ROOT / "data/processed/golden-student-earnings-with-buckets.parquet"
FACULTY_PATH = ROOT / "data/processed/golden_csu_2013-2024.parquet"
OUTPUT = Path(__file__).resolve().parent / "golden_gap_data.csv"

# Load golden datasets
students = pl.read_parquet(STUDENT_PATH).with_columns(
    pl.col("department").str.strip_chars()
)

faculty = pl.read_parquet(FACULTY_PATH).with_columns(
    pl.col("department").str.strip_chars()
)

# Cal Poly SLO bachelor's earnings
students = students.filter(
    pl.col("institution").str.contains(
        "California Polytechnic State University",
        literal=True,
    )
    & (pl.col("credlev") == 3)
    & pl.col("earn_mdn_5yr").is_not_null()
    & (pl.col("department") != "Other")
)

# Median of program medians by bucket
student_summary = students.group_by("department").agg(
    pl.col("earn_mdn_5yr").median().alias("student")
)

# Cal Poly SLO ladder faculty in 2024
faculty = faculty.filter(
    (pl.col("campus") == "Cal Poly San Luis Obispo")
    & (pl.col("year") == 2024)
    & (pl.col("role") == "ladder_faculty")
    & (pl.col("department") != "Other")
    & pl.col("gross_pay").is_not_null()
)

# Median faculty gross pay by bucket
faculty_summary = faculty.group_by("department").agg(
    pl.col("gross_pay").median().alias("faculty")
)

# Match academic buckets
result = (
    student_summary.join(
        faculty_summary,
        on="department",
        how="inner",
    )
    .with_columns(
        (pl.col("faculty") - pl.col("student")).alias("gap")
    )
    .rename({"department": "major"})
    .sort("gap", descending=True)
)

# Save visualization-ready CSV
result.write_csv(OUTPUT)

print("Buckets matched:", result.height)
print(result)
print("\nSaved:", OUTPUT)
