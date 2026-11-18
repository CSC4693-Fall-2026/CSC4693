"""Combine the cleaned UC and CSU faculty-pay Parquets into one standard file.

The two systems use different names for the same basic fields. This script
renames those fields, keeps the detailed records, and checks that no rows are
lost. It does not summarize salaries or remove job roles; those choices can be
made later when the class builds the university/department roll-up.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb


UC_FILENAME = "cleaned_uc_salaries_with_buckets_2013-2024.parquet"
CSU_FILENAME = "csu_depbucket_cleaned_joined_pay_2013-2024.parquet"
OUTPUT_FILENAME = "combined_uc_csu_faculty_pay_2013-2024.parquet"


def quote_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def columns_for(connection: duckdb.DuckDBPyConnection, path: Path) -> set[str]:
    rows = connection.execute(
        "SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet(?))", [str(path)]
    ).fetchall()
    return {row[0] for row in rows}


def write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def combine(input_dir: Path, output_dir: Path) -> None:
    uc_path = input_dir / UC_FILENAME
    csu_path = input_dir / CSU_FILENAME
    for path in (uc_path, csu_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_FILENAME
    connection = duckdb.connect()

    uc_columns = columns_for(connection, uc_path)
    csu_columns = columns_for(connection, csu_path)
    required_uc = {
        "year", "campus", "first_name", "last_name", "title_name", "role",
        "original_department", "department", "gross_pay", "base_pay",
        "overtime_pay", "other_pay",
    }
    required_csu = {
        "year_transparentCA", "school", "name", "title", "original_department",
        "department", "total_pay", "base_pay", "overtime_pay", "other_pay",
    }
    if missing := required_uc - uc_columns:
        raise ValueError(f"UC file is missing columns: {sorted(missing)}")
    if missing := required_csu - csu_columns:
        raise ValueError(f"CSU file is missing columns: {sorted(missing)}")

    # The current CSU notebook writes a role column, but the supplied CSU
    # Parquet does not contain it. Keep it when present; otherwise use NULL and
    # retain the original title so the role can be added after regeneration.
    csu_role = "CAST(role AS VARCHAR)" if "role" in csu_columns else "CAST(NULL AS VARCHAR)"

    uc = quote_path(uc_path)
    csu = quote_path(csu_path)
    out = quote_path(output_path)
    query = f"""
        COPY (
            SELECT
                CAST(year AS SMALLINT) AS year,
                'UC' AS system,
                CAST(campus AS VARCHAR) AS school,
                NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), '') AS faculty_name,
                CAST(first_name AS VARCHAR) AS first_name,
                CAST(last_name AS VARCHAR) AS last_name,
                CAST(title_name AS VARCHAR) AS job_title,
                CAST(role AS VARCHAR) AS faculty_role,
                CAST(original_department AS VARCHAR) AS original_department,
                CAST(department AS VARCHAR) AS department,
                CAST(gross_pay AS BIGINT) AS total_pay,
                CAST(base_pay AS BIGINT) AS base_pay,
                CAST(overtime_pay AS BIGINT) AS overtime_pay,
                CAST(other_pay AS BIGINT) AS other_pay,
                '{UC_FILENAME}' AS source_file
            FROM read_parquet('{uc}')

            UNION ALL

            SELECT
                CAST(year_transparentCA AS SMALLINT) AS year,
                'CSU' AS system,
                CAST(school AS VARCHAR) AS school,
                CAST(name AS VARCHAR) AS faculty_name,
                CAST(NULL AS VARCHAR) AS first_name,
                CAST(NULL AS VARCHAR) AS last_name,
                CAST(title AS VARCHAR) AS job_title,
                {csu_role} AS faculty_role,
                CAST(original_department AS VARCHAR) AS original_department,
                CAST(department AS VARCHAR) AS department,
                CAST(total_pay AS BIGINT) AS total_pay,
                CAST(base_pay AS BIGINT) AS base_pay,
                CAST(overtime_pay AS BIGINT) AS overtime_pay,
                CAST(other_pay AS BIGINT) AS other_pay,
                '{CSU_FILENAME}' AS source_file
            FROM read_parquet('{csu}')
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
    """
    connection.execute(query)

    source_rows = connection.execute(
        """
        SELECT 'UC', COUNT(*) FROM read_parquet(?)
        UNION ALL
        SELECT 'CSU', COUNT(*) FROM read_parquet(?)
        """,
        [str(uc_path), str(csu_path)],
    ).fetchall()
    output_rows = connection.execute(
        "SELECT system, COUNT(*) FROM read_parquet(?) GROUP BY system ORDER BY system",
        [str(output_path)],
    ).fetchall()
    source_counts = dict(source_rows)
    output_counts = dict(output_rows)
    if source_counts != output_counts:
        raise RuntimeError(f"Row-count check failed: source={source_counts}, output={output_counts}")

    summary = connection.execute(
        """
        SELECT
            system,
            COUNT(*) AS rows,
            COUNT(DISTINCT school) AS schools,
            MIN(year) AS first_year,
            MAX(year) AS last_year,
            COUNT(DISTINCT department) AS department_buckets,
            COUNT(*) FILTER (WHERE department IS NULL) AS missing_department_bucket,
            COUNT(*) FILTER (WHERE original_department IS NULL) AS missing_original_department,
            COUNT(*) FILTER (WHERE faculty_role IS NULL) AS missing_faculty_role,
            COUNT(*) FILTER (WHERE faculty_name IS NULL) AS missing_faculty_name
        FROM read_parquet(?)
        GROUP BY system
        ORDER BY system
        """,
        [str(output_path)],
    ).fetchall()
    write_csv(
        output_dir / "combined_faculty_validation.csv",
        [
            "system", "rows", "schools", "first_year", "last_year",
            "department_buckets", "missing_department_bucket",
            "missing_original_department", "missing_faculty_role", "missing_faculty_name",
        ],
        summary,
    )

    bucket_counts = connection.execute(
        """
        SELECT system, department, COUNT(*) AS records
        FROM read_parquet(?)
        GROUP BY system, department
        ORDER BY department, system
        """,
        [str(output_path)],
    ).fetchall()
    write_csv(
        output_dir / "combined_faculty_bucket_counts.csv",
        ["system", "department", "records"],
        bucket_counts,
    )

    print(f"Created {output_path}")
    print(f"UC rows:  {source_counts['UC']:,}")
    print(f"CSU rows: {source_counts['CSU']:,}")
    print(f"Total:    {sum(source_counts.values()):,}")
    if "role" not in csu_columns:
        print("Note: the supplied CSU file has no role column; CSU faculty_role is blank.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path, help="Folder containing the two source Parquets")
    parser.add_argument("output_dir", type=Path, help="Folder for the combined file and checks")
    args = parser.parse_args()
    combine(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
