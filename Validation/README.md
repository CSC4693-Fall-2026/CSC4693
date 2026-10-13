# Student Earnings Bucket Audit

This folder contains a validation pass on the bucketed student earnings data.
The audit checks whether bucket names are consistent, measures how much usable
earnings data is available at one, four, and five years after graduation, and
lists programs that do not have a department bucket.

## Main findings

- `Business, Economics & Finance` was split across two labels because some rows
  contained trailing whitespace.
- `Medicine & Heath Sciences` was corrected to `Medicine & Health Sciences`.
- 26 rows were missing a department bucket.
- Usable earnings values were available for 36.3% of rows at one year, 37.8%
  at four years, and 33.8% at five years. Most unavailable values were marked
  as suppressed.
- Rows for the same school and program should not automatically be treated as
  duplicates because they can represent different credential levels.

## Files

- `student_bucket_audit.py`: performs the audit without overwriting the source
  parquet.
- `student_outputs/student_bucket_coverage.csv`: coverage statistics by bucket.
- `student_outputs/student_bucket_coverage.png`: coverage visualization.
- `student_outputs/unassigned_student_programs.csv`: programs without buckets.

## Usage

```bash
python Validation/student_bucket_audit.py \
  --student-data path/to/student-earnings-with-buckets.parquet \
  --faculty-stats path/to/bucket_pay_stats_by_year.parquet \
  --output-dir Validation/student_outputs
```

The optional faculty statistics file is used to report bucket names that appear
in only one of the two datasets.
