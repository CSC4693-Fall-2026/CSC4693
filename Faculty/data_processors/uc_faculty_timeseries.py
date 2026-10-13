import sys

import polars as pl

SRC = sys.argv[1] if len(sys.argv) > 1 else "Faculty/data/cleaned_salaries.parquet"
LADDER = r"^(act )?(asst |assoc )?prof-(ay|fy)(-b/e/e)?$|^(sr )?lect p?soe"
LECTURER = r"^(sr )?lect-(ay|fy)"
MIN_N = 10

title = pl.col("title_name").str.to_lowercase().str.strip_chars()
faculty = (
    pl.read_parquet(SRC)
    .with_columns(
        pl.when(title.str.contains(LADDER)).then(pl.lit("ladder"))
        .when(title.str.contains(LECTURER)).then(pl.lit("lecturer"))
        .alias("series")
    )
    .filter(pl.col("series").is_not_null())
)

small = pl.col("n") < MIN_N
long = (
    faculty.group_by("year", pl.col("department").alias("bucket"), "series")
    .agg(
        pl.len().alias("n"),
        pl.col("gross_pay").median().alias("median_gross"),
        pl.col("base_pay").median().alias("median_base"),
    )
    .with_columns(
        pl.when(small).then(None).otherwise(pl.col("median_gross")).alias("median_gross"),
        pl.when(small).then(None).otherwise(pl.col("median_base")).alias("median_base"),
    )
    .sort("year", "bucket", "series")
)
long.write_parquet("uc_faculty_timeseries.parquet", compression="zstd")

print(long.group_by("series").agg(pl.len(), pl.col("n").sum()))
