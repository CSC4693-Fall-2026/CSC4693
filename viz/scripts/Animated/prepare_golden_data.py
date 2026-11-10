
from pathlib import Path
import json
import polars as pl

ROOT = Path(__file__).resolve().parents[3]

SOURCE = ROOT / "data/processed/golden-student-earnings-with-buckets.parquet"
OUTPUT = Path(__file__).resolve().parent / "golden_campus_earnings.json"

df = (
    pl.read_parquet(SOURCE)
    .filter(
        (pl.col("credlev") == 3)
        & pl.col("system").is_in(["CSU", "UC"])
    )
)

summary = (
    df.group_by("system", "institution")
    .agg(
        pl.col("earn_mdn_1yr").median().alias("y1"),
        pl.col("earn_mdn_4yr").median().alias("y4"),
        pl.col("earn_mdn_5yr").median().alias("y5"),
        pl.col("earn_mdn_1yr").is_not_null().sum().alias("p1"),
        pl.col("earn_mdn_4yr").is_not_null().sum().alias("p4"),
        pl.col("earn_mdn_5yr").is_not_null().sum().alias("p5"),
    )
    .sort("system", "institution")
)

records = [
    {
        "s": row["system"],
        "n": row["institution"],
        "y1": row["y1"],
        "y4": row["y4"],
        "y5": row["y5"],
        "p1": row["p1"],
        "p4": row["p4"],
        "p5": row["p5"],
    }
    for row in summary.iter_rows(named=True)
]

OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")

print("Campuses generated:", len(records))
print("CSU:", sum(r["s"] == "CSU" for r in records))
print("UC:", sum(r["s"] == "UC" for r in records))
print("Saved:", OUTPUT)
