One-year earnings: UC and CSU

I checked the supplied scorecard_stacked.parquet, which contains bachelor's-degree program records, using the CSU/UC crosswalk from student-data.zip. Each count is a program record, not an individual graduate. Period labels are copied from pooled_award_years; confirm the actual earnings cohorts in the Scorecard cohort map before matching to faculty years.

The summary shows numeric values, PS privacy-suppressed entries, blanks, and other nonnumeric entries separately. Low values below $20,000 and high values above $200,000 are flagged as starting points for review, not automatically errors. Values are median earnings, not individual salaries. An entire blank column in a period needs investigation against the original source files and pipeline before concluding the data does not exist.

To reproduce, run python one_year_eda.py scorecard_stacked.parquet CW2024_prelim.xlsx (requires duckdb, pandas and openpyxl). The crosswalk is in Student-Pipeline-RawFiles inside student-data.zip.
