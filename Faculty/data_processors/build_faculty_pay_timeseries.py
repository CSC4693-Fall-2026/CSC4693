"""Build one faculty pay time series: all departments, then each bucket.

UC rows come from Faculty/data/raw/cleaned_salaries.parquet (2013-2024).
CSU rows come from Faculty/data/raw/csu_depbucket_cleaned_salaries.parquet,
which only has 2024. Medians are computed from person-level pay. A median
is blank when the group has fewer than 10 people.

Title rules for UC match Faculty/data_processors/uc_faculty_timeseries.py.
series "all" is ladder and lecturer together, not every job title in the
source file.
"""

from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
UC_SRC = ROOT / "Faculty" / "data" / "raw" / "cleaned_salaries.parquet"
CSU_SRC = ROOT / "Faculty" / "data" / "raw" / "csu_depbucket_cleaned_salaries.parquet"
OUT = ROOT / "Faculty" / "data" / "faculty_pay_timeseries.parquet"

MIN_N = 10
LADDER = r"^(act )?(asst |assoc )?prof-(ay|fy)(-b/e/e)?$|^(sr )?lect p?soe"
LECTURER = r"^(sr )?lect-(ay|fy)"


def _uc_series(title: pl.Expr) -> pl.Expr:
    return (
        pl.when(title.str.contains(LADDER))
        .then(pl.lit("ladder"))
        .when(title.str.contains(LECTURER))
        .then(pl.lit("lecturer"))
    )


def _csu_series(title: pl.Expr) -> pl.Expr:
    # Adjunct and lecturer are the non-ladder teaching titles in the CSU file.
    # "Instructional Faculty" / "Instr Fac" is the ladder title some campuses use
    # instead of Professor.
    lecturer = title.str.contains("lecturer") | title.str.contains("adjunct") | (
        title.str.contains("instructor") & ~title.str.contains("instructional")
    )
    ladder = (
        title.str.contains("professor")
        | title.str.contains("instructional faculty")
        | title.str.contains("instr fac")
    )
    return pl.when(lecturer).then(pl.lit("lecturer")).when(ladder).then(pl.lit("ladder"))


def load_people() -> pl.DataFrame:
    uc = (
        pl.read_parquet(UC_SRC)
        .select(
            pl.col("year").cast(pl.Int16),
            pl.lit("UC").alias("system"),
            pl.col("department").alias("bucket"),
            _uc_series(pl.col("title_name").str.to_lowercase().str.strip_chars()).alias("series"),
            pl.col("gross_pay").cast(pl.Float64),
            pl.col("base_pay").cast(pl.Float64),
        )
    )
    csu = (
        pl.read_parquet(CSU_SRC)
        .select(
            pl.col("year_transparentCA").cast(pl.Int16).alias("year"),
            pl.lit("CSU").alias("system"),
            pl.col("department").alias("bucket"),
            _csu_series(pl.col("title").str.to_lowercase().str.strip_chars()).alias("series"),
            pl.col("total_pay").cast(pl.Float64).alias("gross_pay"),
            pl.col("base_pay").cast(pl.Float64),
        )
    )
    return pl.concat([uc, csu]).filter(pl.col("series").is_not_null())


def _summarize(df: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    out = df.group_by(keys).agg(
        pl.len().cast(pl.UInt32).alias("n"),
        pl.col("gross_pay").median().alias("median_gross"),
        pl.col("base_pay").median().alias("median_base"),
    )
    small = pl.col("n") < MIN_N
    return out.with_columns(
        pl.when(small).then(None).otherwise(pl.col("median_gross")).alias("median_gross"),
        pl.when(small).then(None).otherwise(pl.col("median_base")).alias("median_base"),
    )


def build(people: pl.DataFrame) -> pl.DataFrame:
    parts: list[pl.DataFrame] = []
    slices = {
        "ladder": people.filter(pl.col("series") == "ladder"),
        "lecturer": people.filter(pl.col("series") == "lecturer"),
        "all": people,
    }
    for series_name, sub in slices.items():
        by_bucket = _summarize(sub, ["year", "system", "bucket"]).with_columns(
            pl.lit(series_name).alias("series")
        )
        overall = _summarize(sub, ["year", "system"]).with_columns(
            pl.lit("All").alias("bucket"),
            pl.lit(series_name).alias("series"),
        )
        parts.extend([by_bucket, overall])
    return (
        pl.concat(parts, how="diagonal")
        .with_columns(pl.lit("nominal").alias("price_basis"))
        .select(
            "year",
            "system",
            "bucket",
            "series",
            "n",
            "median_gross",
            "median_base",
            "price_basis",
        )
        .sort("system", "series", "bucket", "year")
    )


def main() -> None:
    people = load_people()
    out = build(people)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(OUT, compression="zstd")
    print(f"wrote {OUT} rows={out.height}")
    print(
        out.group_by("system", "series").agg(
            pl.col("year").min().alias("year_min"),
            pl.col("year").max().alias("year_max"),
            pl.len().alias("rows"),
        )
    )


if __name__ == "__main__":
    main()
