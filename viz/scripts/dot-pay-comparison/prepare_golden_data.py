
from pathlib import Path
import json
import polars as pl

ROOT = Path(__file__).resolve().parents[3]

STUDENT_PATH = ROOT / "data/processed/golden-student-earnings-with-buckets.parquet"
FACULTY_PATH = ROOT / "data/processed/golden_csu_2013-2024.parquet"

OUTPUT = Path(__file__).resolve().parent / "pay-constants.js"

students = (
    pl.read_parquet(STUDENT_PATH)
    .with_columns(pl.col("department").str.strip_chars())
    .filter(
        pl.col("institution").str.contains(
            "California Polytechnic State University",
            literal=True
        )
        & (pl.col("credlev") == 3)
        & pl.col("earn_mdn_5yr").is_not_null()
    )
)

faculty = (
    pl.read_parquet(FACULTY_PATH)
    .with_columns(pl.col("department").str.strip_chars())
    .filter(
        (pl.col("campus") == "Cal Poly San Luis Obispo")
        & (pl.col("year") == 2024)
        & (pl.col("role") == "ladder_faculty")
        & pl.col("gross_pay").is_not_null()
    )
)

student_stats = students.group_by("department").agg(
    pl.len().alias("student_count"),
    pl.col("earn_mdn_5yr").mean().alias("student_mean"),
    pl.col("earn_mdn_5yr").std().alias("student_std")
)

faculty_stats = faculty.group_by("department").agg(
    pl.len().alias("faculty_count"),
    pl.col("gross_pay").mean().alias("faculty_mean"),
    pl.col("gross_pay").std().alias("faculty_std")
)

combined = (
    student_stats.join(
        faculty_stats,
        on="department",
        how="inner"
    )
    .filter(
        (pl.col("student_count") >= 2)
        & (pl.col("faculty_count") >= 2)
        & pl.col("student_std").is_not_null()
        & pl.col("faculty_std").is_not_null()
    )
    .sort("department")
)

records = [
    {
        "major": row["department"],
        "faculty": {
            "mean": round(row["faculty_mean"], 2),
            "std": round(row["faculty_std"], 2)
        },
        "industry": {
            "mean": round(row["student_mean"], 2),
            "std": round(row["student_std"], 2)
        }
    }
    for row in combined.iter_rows(named=True)
]

OUTPUT.write_text(
    "// Generated from golden CSU faculty and student earnings Parquets.\n"
    "// Dots are simulated from summary statistics, not individual observations.\n"
    "// 'industry' represents program-level 5-year earnings medians.\n"
    "window.PAY_DISTRIBUTIONS = "
    + json.dumps(records, indent=2)
    + ";\n",
    encoding="utf-8"
)

print("Buckets generated:", len(records))
print(combined.select("department", "student_count", "faculty_count"))
print("Saved:", OUTPUT)
