"""Audit student earnings bucket coverage and create a coverage chart.

Example:
    python Validation/student_bucket_audit.py \
        --student-data student-earnings-with-buckets.parquet \
        --faculty-stats bucket_pay_stats_by_year.parquet \
        --output-dir Validation/student_outputs

The source parquet is never overwritten.
"""

from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl


HORIZONS = ("1yr", "4yr", "5yr")
DEPARTMENT_FIXES = {
    "Medicine & Heath Sciences": "Medicine & Health Sciences",
}


def normalize_departments(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("department")
        .str.strip_chars()
        .replace(DEPARTMENT_FIXES)
        .alias("department")
    )


def build_coverage(df: pl.DataFrame) -> pl.DataFrame:
    expressions = [
        pl.len().alias("rows"),
        pl.col("program").n_unique().alias("programs"),
        pl.col("institution").n_unique().alias("schools"),
    ]

    for horizon in HORIZONS:
        pay = f"earn_mdn_{horizon}"
        status = f"status_{horizon}"
        expressions.extend(
            [
                pl.col(pay).is_not_null().sum().alias(f"usable_{horizon}"),
                pl.col("institution")
                .filter(pl.col(pay).is_not_null())
                .n_unique()
                .alias(f"schools_{horizon}"),
                (pl.col(status) == "suppressed")
                .sum()
                .alias(f"suppressed_{horizon}"),
            ]
        )

    return (
        df.filter(pl.col("department").is_not_null())
        .group_by("department")
        .agg(expressions)
        .with_columns(
            *[
                (pl.col(f"usable_{horizon}") / pl.col("rows"))
                .alias(f"usable_rate_{horizon}")
                for horizon in HORIZONS
            ]
        )
        .sort("department")
    )


def make_chart(coverage: pl.DataFrame, output_path: Path) -> None:
    chart = coverage.select(
        "department", *[f"usable_rate_{horizon}" for horizon in HORIZONS]
    ).to_pandas()

    chart = chart.set_index("department") * 100
    ax = chart.rename(
        columns={
            "usable_rate_1yr": "1 year",
            "usable_rate_4yr": "4 years",
            "usable_rate_5yr": "5 years",
        }
    ).plot(kind="bar", figsize=(13, 6), width=0.82)

    ax.set_title("Usable student earnings records by department bucket")
    ax.set_xlabel("Department bucket")
    ax.set_ylabel("Rows with usable earnings (%)")
    ax.set_ylim(0, 100)
    ax.legend(title="Time after graduation")
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--student-data", type=Path, required=True)
    parser.add_argument("--faculty-stats", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("student_outputs"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = pl.read_parquet(args.student_data)
    cleaned = normalize_departments(raw)
    coverage = build_coverage(cleaned)

    coverage.write_csv(args.output_dir / "student_bucket_coverage.csv")
    make_chart(coverage, args.output_dir / "student_bucket_coverage.png")

    unassigned = (
        cleaned.filter(pl.col("department").is_null())
        .group_by("cipcode", "program")
        .agg(
            pl.len().alias("rows"),
            pl.col("institution").n_unique().alias("schools"),
            *[
                pl.col(f"earn_mdn_{horizon}")
                .is_not_null()
                .sum()
                .alias(f"usable_{horizon}")
                for horizon in HORIZONS
            ],
        )
        .sort("cipcode")
    )
    unassigned.write_csv(args.output_dir / "unassigned_student_programs.csv")

    print(f"Student rows: {cleaned.height:,}")
    print(f"Unassigned rows: {cleaned['department'].null_count():,}")
    for horizon in HORIZONS:
        usable = cleaned[f"earn_mdn_{horizon}"].is_not_null().sum()
        print(
            f"Usable {horizon} earnings: {usable:,}/{cleaned.height:,} "
            f"({usable / cleaned.height:.1%})"
        )

    if args.faculty_stats:
        faculty = pl.read_parquet(args.faculty_stats)
        student_buckets = set(cleaned["department"].drop_nulls().unique())
        faculty_buckets = set(faculty["bucket"].drop_nulls().unique())
        print("Student-only buckets:", sorted(student_buckets - faculty_buckets))
        print("Faculty-only buckets:", sorted(faculty_buckets - student_buckets))

    print("\nUnassigned programs:")
    print(unassigned)
    print(f"\nOutputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
