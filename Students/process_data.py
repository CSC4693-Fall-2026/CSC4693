import polars as pl

# Needs Most-Recent-Cohorts-Field-of-Study.csv, Most-Recent-Cohorts-Institution.csv, CW2024_prelim.xlsx from https://collegescorecard.ed.gov/data/

def main():
    print("Scanning CSV files...")

    horizons = ["1YR", "4YR", "5YR"]

    # Cols holding "PS" (privacy suppressed), must be read as String first
    suppressed_cols = (
        [f"EARN_MDN_{h}" for h in horizons]
        + [f"EARN_COUNT_WNE_{h}" for h in horizons]
        + ["IPEDSCOUNT1"]
    )

    # Scorecard writes literal "NA" in some cols, including UNITID
    nulls = ["NA", "NULL", ""]

    # Helper to turn suppressed text into numbers
    def clean_suppressed(col_name, dtype=pl.Float64):
        return (
            pl.col(col_name)
            .str.strip_chars()
            .replace(["PS", ""], None)
            .cast(dtype, strict=False)
        )

    # Showing better documented CA public universities for demo purposes
    systems = {
        "California State University": "CSU",
        "University of California": "UC",
    }
    ca = (
        pl.read_excel("data/raw/CW2024_prelim.xlsx", sheet_name="Crosswalk")
        .select(
            pl.col("IPEDSMatch").cast(pl.Int64, strict=False).alias("UNITID"),
            pl.col("f1sysnam").replace_strict(systems, default=None).alias("system"),
        )
        .drop_nulls()
        .unique(subset="UNITID")
    )

    # Institution metadata
    meta = pl.scan_csv(
        "data/raw/Most-Recent-Cohorts-Institution.csv",
        schema_overrides={c: pl.String for c in ["UGDS"]},
        null_values=nulls,
        infer_schema_length=10000,
    ).select(
        pl.col("UNITID").cast(pl.Int64),
        pl.col("CITY").alias("city"),
        pl.col("STABBR").alias("state"),
        pl.col("UGDS").cast(pl.Int32, strict=False).alias("undergrad_enrollment"),
    )

    df = pl.scan_csv(
        "data/raw/Most-Recent-Cohorts-Field-of-Study.csv",
        schema_overrides={c: pl.String for c in suppressed_cols + ["CIPCODE"]},
        null_values=nulls,
        infer_schema_length=10000,
    )

    df = (
        df.with_columns(pl.col("UNITID").cast(pl.Int64))
        .join(ca.lazy(), on="UNITID", how="inner")
        .join(meta, on="UNITID", how="left")
        .with_columns(
            # Keep as text, CIP codes can start with a zero (0110)
            pl.col("CIPCODE").str.zfill(4).alias("cipcode"),

            *[clean_suppressed(f"EARN_MDN_{h}").alias(f"earn_mdn_{h.lower()}")
              for h in horizons],
            *[clean_suppressed(f"EARN_COUNT_WNE_{h}", pl.Int32).alias(f"earn_count_{h.lower()}")
              for h in horizons],
            clean_suppressed("IPEDSCOUNT1", pl.Int32).alias("completions"),

            # Why a value is missing: "PS" = withheld for privacy, blank = not reported
            *[pl.when(pl.col(f"EARN_MDN_{h}") == "PS").then(pl.lit("suppressed"))
               .when(pl.col(f"EARN_MDN_{h}").is_null()).then(pl.lit("not_reported"))
               .otherwise(pl.lit("usable"))
               .cast(pl.Categorical).alias(f"status_{h.lower()}")
              for h in horizons],
        )
        .select(
            pl.col("UNITID").alias("unitid"),
            pl.col("INSTNM").alias("institution"),
            "system", "city", "state", "undergrad_enrollment",
            "cipcode",
            pl.col("CIPDESC").alias("program"),
            pl.col("CREDLEV").cast(pl.Int16).alias("credlev"),
            "completions",
            *[f"earn_mdn_{h.lower()}" for h in horizons],
            *[f"earn_count_{h.lower()}" for h in horizons],
            *[f"status_{h.lower()}" for h in horizons],
        )
        .sort(["system", "institution", "cipcode", "credlev"])
    )

    final_df = df.collect()
    final_df.write_parquet("data/student-earnings.parquet", compression="zstd")

    print(f"Processed {final_df.height:,} records.")
    schema = final_df.schema
    for col_name, dtype in schema.items():
        print(f"{col_name}: {dtype}")


if __name__ == "__main__":
    main()
