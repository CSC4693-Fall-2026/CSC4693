import duckdb
import polars as pl
from pathlib import Path

# Joins UC faculty pay to UC graduate earnings by campus and department bucket

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent

FACULTY = ROOT / "Faculty" / "data" / "cleaned_salaries.parquet"
STUDENTS = ROOT / "Students" / "data" / "student-earnings.parquet"
CROSSWALK = HERE / "cip_to_bucket.csv"
OUT = HERE / "uc_comparison"

YEAR = 2023      # latest full year of faculty pay
MIN_N = 10       # our agreed minimum n per aggregate

# The 9 undergrad campuses, UCSF and UC SF Law have no bachelor's graduates
CAMPUS_UNITID = {
    "berkeley": 110635, "davis": 110644, "irvine": 110653, "los angeles": 110662,
    "merced": 445188, "riverside": 110671, "san diego": 110680,
    "santa barbara": 110705, "santa cruz": 110714,
}

# Matching on title, not department, keeps out grad researchers and postdocs
LADDER = r"^(act )?(asst |assoc )?prof-(ay|fy)(-b/e/e)?$|^(sr )?lect p?soe"
LECTURER = r"^(sr )?lect-(ay|fy)"


def main():
    print("Loading faculty and graduate data...")

    campuses = pl.DataFrame({"campus": list(CAMPUS_UNITID), "unitid": list(CAMPUS_UNITID.values())})

    faculty = (
        pl.read_parquet(FACULTY)
        .filter(pl.col("year") == YEAR)
        .with_columns(
            pl.when(pl.col("title_name").str.contains(LADDER)).then(pl.lit("ladder"))
            .when(pl.col("title_name").str.contains(LECTURER)).then(pl.lit("lecturer"))
            .otherwise(None)
            .alias("series")
        )
        # Medicine has no fair bachelor's-level comparison
        .filter(pl.col("series").is_not_null() & (pl.col("department") != "Medicine & Health Sciences"))
        .join(campuses, on="campus", how="inner")
    )

    # A 4-digit code overrides its 2-digit family
    xw = pl.read_csv(CROSSWALK, schema_overrides={"cip": pl.String})
    students = (
        pl.read_parquet(STUDENTS)
        .filter((pl.col("system") == "UC") & (pl.col("credlev") == 3))
        .with_columns(pl.col("cipcode").str.slice(0, 2).alias("cip2"))
        .join(xw.select(pl.col("cip").alias("cipcode"), pl.col("bucket").alias("b4")), on="cipcode", how="left")
        .join(xw.select(pl.col("cip").alias("cip2"), pl.col("bucket").alias("b2")), on="cip2", how="left")
        .with_columns(pl.coalesce("b4", "b2").alias("department"))
    )

    unmapped = students.filter(pl.col("department").is_null())
    if unmapped.height:
        print(f"Unmapped CIP codes ({unmapped['completions'].sum():,} graduates):")
        for cip, prog in unmapped.select("cipcode", "program").unique().sort("cipcode").iter_rows():
            print(f"  {cip} {prog}")

    duckdb.connect()

    # Sum split appointments so each person counts once
    faculty_agg = duckdb.sql("""
    WITH people AS (
        SELECT unitid, campus, department, series, first_name, last_name,
            SUM(base_pay) AS base_pay, SUM(gross_pay) AS gross_pay
        FROM faculty
        GROUP BY unitid, campus, department, series, first_name, last_name
    )
    SELECT unitid, campus, department, series,
        COUNT(*) AS faculty_n,
        MEDIAN(base_pay) AS faculty_median_base,
        MEDIAN(gross_pay) AS faculty_median_gross
    FROM people
    GROUP BY unitid, campus, department, series
    """).pl()

    # Scorecard only publishes per-program medians, so weight them by graduate count
    grad_agg = duckdb.sql("""
    SELECT unitid, department,
        CAST(SUM(earn_count_1yr) FILTER (WHERE earn_mdn_1yr IS NOT NULL) AS INTEGER) AS grad_n_1yr,
        SUM(earn_mdn_1yr * earn_count_1yr) FILTER (WHERE earn_mdn_1yr IS NOT NULL)
            / SUM(earn_count_1yr) FILTER (WHERE earn_mdn_1yr IS NOT NULL) AS grad_earn_1yr,
        CAST(SUM(earn_count_5yr) FILTER (WHERE earn_mdn_5yr IS NOT NULL) AS INTEGER) AS grad_n_5yr,
        SUM(earn_mdn_5yr * earn_count_5yr) FILTER (WHERE earn_mdn_5yr IS NOT NULL)
            / SUM(earn_count_5yr) FILTER (WHERE earn_mdn_5yr IS NOT NULL) AS grad_earn_5yr
    FROM students
    WHERE department IS NOT NULL AND department != 'Medicine & Health Sciences'
    GROUP BY unitid, department
    """).pl()

    final_df = duckdb.sql(f"""
    SELECT f.campus, f.unitid, f.department, f.series,
        f.faculty_n, f.faculty_median_base, f.faculty_median_gross,
        g.grad_n_1yr, ROUND(g.grad_earn_1yr) AS grad_earn_1yr,
        g.grad_n_5yr, ROUND(g.grad_earn_5yr) AS grad_earn_5yr,
        -- gross is the headline, grad earnings are annual and base pay is 9-month
        ROUND(g.grad_earn_1yr / f.faculty_median_gross, 3) AS ratio_1yr,
        ROUND(g.grad_earn_5yr / f.faculty_median_gross, 3) AS ratio_5yr,
        ROUND(g.grad_earn_5yr / f.faculty_median_base, 3) AS ratio_5yr_base,
        (f.faculty_n >= {MIN_N} AND COALESCE(g.grad_n_5yr, 0) >= {MIN_N}) AS meets_min_n
    FROM faculty_agg f
    JOIN grad_agg g USING (unitid, department)
    ORDER BY f.series, f.department, f.campus
    """).pl()

    final_df.write_parquet(f"{OUT}.parquet", compression="zstd")
    final_df.write_csv(f"{OUT}.csv")

    print(f"Processed {final_df.height:,} records "
          f"({final_df.filter(pl.col('meets_min_n')).height} meet n >= {MIN_N}).")
    for col_name, dtype in final_df.schema.items():
        print(f"{col_name}: {dtype}")


if __name__ == "__main__":
    main()
