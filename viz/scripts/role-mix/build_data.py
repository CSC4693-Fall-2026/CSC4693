import json
import sys
from pathlib import Path

import polars as pl

SRC = sys.argv[1]
ROLES = ["ladder_faculty", "lecturer", "clinical_adjunct_faculty", "recalled_emeriti", "teaching_assistant",
         "grad_student_researcher", "postdoc", "researcher_specialist_librarian"]

redacted = pl.col("first_name") == "****"
people = (
    pl.read_parquet(SRC)
    .filter(pl.col("role").is_in(ROLES) & (pl.col("department") != "Other"))
    .with_row_index("row")
    .with_columns(
        pl.when(redacted).then(pl.format("r{}", "row"))
        .otherwise(pl.concat_str("campus", "first_name", "last_name", separator="|")).alias("pid")
    )
    .group_by("year", pl.col("department").alias("bucket"), "role", "pid")
    .agg(pl.col("gross_pay").cast(pl.Int64).sum())
)
rows = (
    people.group_by("year", "bucket", "role")
    .agg(
        pl.len().alias("people"),
        pl.col("gross_pay").sum().alias("spend"),
        pl.col("gross_pay").median().round(0).cast(pl.Int64).alias("median"),
    )
    .sort("year", "bucket", "role")
)
(Path(__file__).parent / "role-mix-data.js").write_text("window.ROLE_MIX = " + json.dumps(rows.rows(named=True), separators=(",", ":")) + ";\n")
print(rows.height)
