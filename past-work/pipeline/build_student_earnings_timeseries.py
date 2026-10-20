"""Build a student earnings time series from College Scorecard field-of-study files.

Scorecard names each yearly file after its debt cohort, and leaves most
earnings columns empty. The one-year-after-completion series below is the
sequence in FieldOfStudy_Cohort_Map (College Scorecard data dictionary):

  file                      column            earnings cohort          dollars
  FieldOfStudyData1516_1617 EARN_MDN_HI_1YR   2014-15 and 2015-16      2018
  FieldOfStudyData1617_1718 EARN_MDN_HI_1YR   2015-16 and 2016-17      2019
  FieldOfStudyData1718_1819 EARN_MDN_HI_1YR   2016-17 and 2017-18      2020
  FieldOfStudyData1819_1920 EARN_MDN_1YR      2017-18 and 2018-19      2021
  FieldOfStudyData1920_2021 EARN_MDN_1YR      2018-19 and 2019-20      2022

The HI suffix is the older variable. Later files publish EARN_MDN_1YR instead.
Counts are the matching EARN_COUNT_WNE_* column. A bucket value is the
count-weighted mean of program medians, because Scorecard does not publish
person-level wages. It is blank when that summed count is under 10.

CIP codes are mapped with data/student/cip_department_buckets.csv. Unlisted
programs stay in bucket "Other". "All" is recomputed from programs.
"""

import os
import zipfile
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
MAP_PATH = ROOT / "data" / "student" / "cip_department_buckets.csv"
OUT = ROOT / "processing" / "student" / "output" / "student_earnings_timeseries.parquet"
ZIP_URL = (
    "https://ed-public-download.scorecard.network/downloads/"
    "College_Scorecard_Raw_Data_06102026.zip"
)
ZIP_NAME = "College_Scorecard_Raw_Data_06102026.zip"
INNER_PREFIX = "College_Scorecard_Raw_Data_06032026/"

# Earnings cohort, not the debt-cohort years in the file name.
POOLS = [
    {
        "file": "FieldOfStudyData1516_1617_PP.csv",
        "median_col": "EARN_MDN_HI_1YR",
        "count_col": "EARN_COUNT_WNE_HI_1YR",
        "pool_start": 2014,
        "pool_end": 2016,
        "award_pool": "2014-15/2015-16",
        "measured_cy": "2016/2017",
        "dollar_year": 2018,
    },
    {
        "file": "FieldOfStudyData1617_1718_PP.csv",
        "median_col": "EARN_MDN_HI_1YR",
        "count_col": "EARN_COUNT_WNE_HI_1YR",
        "pool_start": 2015,
        "pool_end": 2017,
        "award_pool": "2015-16/2016-17",
        "measured_cy": "2017/2018",
        "dollar_year": 2019,
    },
    {
        "file": "FieldOfStudyData1718_1819_PP.csv",
        "median_col": "EARN_MDN_HI_1YR",
        "count_col": "EARN_COUNT_WNE_HI_1YR",
        "pool_start": 2016,
        "pool_end": 2018,
        "award_pool": "2016-17/2017-18",
        "measured_cy": "2018/2019",
        "dollar_year": 2020,
    },
    {
        "file": "FieldOfStudyData1819_1920_PP.csv",
        "median_col": "EARN_MDN_1YR",
        "count_col": "EARN_COUNT_WNE_1YR",
        "pool_start": 2017,
        "pool_end": 2019,
        "award_pool": "2017-18/2018-19",
        "measured_cy": "2019/2020",
        "dollar_year": 2021,
    },
    {
        "file": "FieldOfStudyData1920_2021_PP.csv",
        "median_col": "EARN_MDN_1YR",
        "count_col": "EARN_COUNT_WNE_1YR",
        "pool_start": 2018,
        "pool_end": 2020,
        "award_pool": "2018-19/2019-20",
        "measured_cy": "2020/2021",
        "dollar_year": 2022,
    },
]
SYSTEMS = {
    "California State University": "CSU",
    "University of California": "UC",
}
FACULTY_BUCKETS = {
    "Agriculture, Food & Animal",
    "Architecture & Environmental Design",
    "Business, Economics & Finance",
    "Computer Science",
    "Education & Public Administration",
    "Engineering",
    "Humanities & Languages",
    "Medicine & Health Sciences",
    "Science & Mathematics",
    "Social Sciences & Communication",
}
CREDENTIAL = {
    1: "Undergraduate Certificate",
    2: "Associate's Degree",
    3: "Bachelor's Degree",
    4: "Post-Baccalaureate Certificate",
    5: "Master's Degree",
    6: "Doctoral Degree",
    7: "First Professional Degree",
    8: "Graduate Certificate",
}
MIN_N = 10
ID_COLS = ["UNITID", "OPEID6", "CIPCODE", "CREDLEV"]


def zip_path() -> Path:
    candidates = [
        Path(os.environ.get("TEMP", "/tmp")) / "csc4693-scorecard" / ZIP_NAME,
        ROOT / "Students" / "data" / "raw" / ZIP_NAME,
    ]
    for path in candidates:
        if path.exists():
            return path
    raise SystemExit(f"Scorecard zip not found. Download {ZIP_URL} to {candidates[0]}")


def load_bucket_map() -> pl.DataFrame:
    raw = pl.read_csv(MAP_PATH, schema_overrides={"CIPCODE": pl.Utf8, "DEPT": pl.Utf8})
    mapped = raw.select(
        pl.col("CIPCODE").str.replace_all(r"\D", "").str.zfill(4).alias("cip4"),
        pl.col("DEPT")
        .str.strip_chars()
        .str.strip_chars('"')
        .str.replace(", &", " &")
        .str.strip_chars()
        .alias("bucket"),
    ).unique(subset="cip4")
    unknown = set(mapped["bucket"].unique().to_list()) - FACULTY_BUCKETS
    if unknown:
        raise SystemExit(f"CIP map has buckets that are not faculty buckets: {unknown}")
    return mapped


def load_systems(zpath: Path) -> pl.DataFrame:
    xlsx_name = INNER_PREFIX + "Crosswalks/CW2024_prelim.xlsx"
    dest = zpath.parent / "CW2024_prelim.xlsx"
    if not dest.exists():
        with zipfile.ZipFile(zpath) as zf:
            dest.write_bytes(zf.read(xlsx_name))
    cross = pl.read_excel(dest, sheet_name="Crosswalk").select(
        pl.col("IPEDSMatch").cast(pl.Int64, strict=False).alias("unitid"),
        pl.col("f1sysnam").replace_strict(SYSTEMS, default=None).alias("system"),
    )
    return cross.drop_nulls().unique(subset="unitid")


def _clean_number(col: str, dtype: pl.DataType) -> pl.Expr:
    return (
        pl.col(col)
        .str.strip_chars()
        .replace(["", "NA", "NULL", "PS", "PrivacySuppressed"], None)
        .cast(dtype, strict=False)
    )


def read_pool(zpath: Path, spec: dict) -> pl.DataFrame:
    cols = ID_COLS + [spec["median_col"], spec["count_col"]]
    with zipfile.ZipFile(zpath) as zf:
        raw = zf.read(INNER_PREFIX + spec["file"])
    tmp = zpath.parent / spec["file"]
    tmp.write_bytes(raw)
    try:
        df = pl.read_csv(
            tmp,
            columns=cols,
            schema_overrides={c: pl.Utf8 for c in cols},
            infer_schema_length=0,
        )
    finally:
        tmp.unlink(missing_ok=True)
    return df.with_columns(
        pl.lit(spec["pool_start"]).cast(pl.Int16).alias("pool_start"),
        pl.lit(spec["pool_end"]).cast(pl.Int16).alias("pool_end"),
        pl.lit(spec["award_pool"]).alias("award_pool"),
        pl.lit(spec["measured_cy"]).alias("measured_cy"),
        pl.lit(spec["dollar_year"]).cast(pl.Int16).alias("dollar_year"),
        pl.lit(spec["median_col"]).alias("metric"),
        pl.col("UNITID").cast(pl.Int64, strict=False).alias("unitid"),
        pl.col("OPEID6").alias("opeid6"),
        pl.col("CIPCODE").str.replace_all(r"\D", "").str.zfill(4).alias("cip4"),
        _clean_number("CREDLEV", pl.Int16).alias("credlev"),
        _clean_number(spec["median_col"], pl.Float64).alias("median"),
        _clean_number(spec["count_col"], pl.Float64).alias("count"),
    )


def programs_for_pool(df: pl.DataFrame, systems: pl.DataFrame, buckets: pl.DataFrame) -> pl.DataFrame:
    joined = (
        df.join(systems, on="unitid", how="inner")
        .join(buckets, on="cip4", how="left")
        .with_columns(pl.col("bucket").fill_null("Other"))
    )
    # Earnings are repeated across UNITIDs that share an OPEID6. A missing
    # OPEID falls back to UNITID so those rows are not collapsed together.
    return (
        joined.with_columns(
            pl.coalesce(
                pl.when(pl.col("opeid6").str.len_chars() > 0).then(pl.col("opeid6")),
                pl.col("unitid").cast(pl.Utf8),
            ).alias("dedupe_key")
        )
        .sort("count", descending=True, nulls_last=True)
        .unique(
            subset=[
                "dedupe_key",
                "cip4",
                "credlev",
                "system",
                "award_pool",
            ],
            keep="first",
        )
        .select(
            "pool_start",
            "pool_end",
            "award_pool",
            "measured_cy",
            "dollar_year",
            "metric",
            "system",
            "bucket",
            "credlev",
            "median",
            "count",
        )
    )


def rollup(programs: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    usable = pl.col("median").is_not_null() & pl.col("count").is_not_null() & (pl.col("count") > 0)
    flagged = programs.with_columns(usable.alias("usable"))
    out = flagged.group_by(keys).agg(
        pl.col("count").filter(pl.col("usable")).sum().alias("n"),
        pl.col("usable").sum().cast(pl.UInt32).alias("n_programs"),
        (pl.col("median") * pl.col("count")).filter(pl.col("usable")).sum().alias("weighted"),
        (~pl.col("usable")).sum().cast(pl.UInt32).alias("n_suppressed"),
        pl.col("measured_cy").first(),
        pl.col("dollar_year").first(),
        pl.col("metric").first(),
    )
    small = pl.col("n").is_null() | (pl.col("n") < MIN_N)
    return out.with_columns(
        pl.col("n").fill_null(0).cast(pl.UInt32),
        pl.when(small).then(None).otherwise(pl.col("weighted") / pl.col("n")).alias("earn_mdn_1yr_wavg"),
    ).drop("weighted")


def add_aggregates(programs: pl.DataFrame) -> pl.DataFrame:
    keys = ["pool_start", "pool_end", "award_pool", "credlev"]
    parts = [
        rollup(programs, keys + ["system", "bucket"]),
        rollup(programs, keys + ["system"]).with_columns(pl.lit("All").alias("bucket")),
        rollup(programs, keys + ["bucket"]).with_columns(pl.lit("All").alias("system")),
        rollup(programs, keys).with_columns(
            pl.lit("All").alias("system"),
            pl.lit("All").alias("bucket"),
        ),
    ]
    cred = pl.DataFrame(
        {"credlev": list(CREDENTIAL), "credential": list(CREDENTIAL.values())}
    ).with_columns(pl.col("credlev").cast(pl.Int16))
    return (
        pl.concat(parts, how="diagonal")
        .join(cred, on="credlev", how="left")
        .with_columns(pl.lit("1yr_after_completion").alias("horizon"))
        .select(
            "pool_start",
            "pool_end",
            "award_pool",
            "measured_cy",
            "dollar_year",
            "horizon",
            "metric",
            "system",
            "bucket",
            "credlev",
            "credential",
            "n",
            "n_programs",
            "n_suppressed",
            "earn_mdn_1yr_wavg",
        )
        .sort("pool_start", "credlev", "system", "bucket")
    )


def main() -> None:
    zpath = zip_path()
    buckets = load_bucket_map()
    systems = load_systems(zpath)
    frames: list[pl.DataFrame] = []
    for spec in POOLS:
        pool = read_pool(zpath, spec)
        usable = pool.filter(pl.col("median").is_not_null()).height
        print(f"{spec['award_pool']} {spec['median_col']}: {usable:,} programs with a median, of {pool.height:,}")
        if usable == 0:
            raise SystemExit(f"no earnings in {spec['file']} column {spec['median_col']}")
        frames.append(programs_for_pool(pool, systems, buckets))
    programs = pl.concat(frames)
    mapped = programs.filter(pl.col("bucket") != "Other").height
    print(f"UC/CSU programs {programs.height:,}; CIP-mapped {mapped:,}; Other {programs.height - mapped:,}")
    out = add_aggregates(programs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(OUT, compression="zstd")
    print(f"wrote {OUT} rows={out.height}")
    print(
        out.filter((pl.col("bucket") == "All") & (pl.col("credlev") == 3))
        .select("award_pool", "system", "dollar_year", "n", "n_programs", "earn_mdn_1yr_wavg")
        .sort("award_pool", "system")
    )


if __name__ == "__main__":
    main()
