"""Summarize one-year earnings for UC and CSU bachelor's program records.

Usage: python one_year_eda.py scorecard_stacked.parquet CW2024_prelim.xlsx
Install dependencies: duckdb, pandas, openpyxl. Outputs are written to the
current directory. The crosswalk is included in the team's student-data.zip.
"""
import sys
import duckdb
import pandas as pd

if len(sys.argv) != 3:
    raise SystemExit('Usage: python one_year_eda.py scorecard_stacked.parquet CW2024_prelim.xlsx')
parquet, crosswalk = sys.argv[1:]
schools = pd.read_excel(crosswalk, sheet_name='Crosswalk', usecols=['IPEDSMatch', 'f1sysnam'])
schools = schools[schools.f1sysnam.isin(['California State University', 'University of California'])].dropna().drop_duplicates()
schools['IPEDSMatch'] = schools.IPEDSMatch.astype('int64').astype(str)
assert not schools.duplicated('IPEDSMatch').any(), 'Crosswalk has duplicate school identifiers'
con = duckdb.connect()
con.register('schools', schools)
con.execute('''CREATE TEMP TABLE base AS SELECT p.UNITID, p.INSTNM, p.CIPCODE, p.CIPDESC, p.CREDLEV, p.pooled_award_years, p.EARN_MDN_1YR, s.f1sysnam AS system, TRY_CAST(p.EARN_MDN_1YR AS DOUBLE) AS earnings FROM read_parquet(?) p JOIN schools s ON p.UNITID = s.IPEDSMatch WHERE p.pooled_award_years IN ('2015-16 & 2016-17','2016-17 & 2017-18','2017-18 & 2018-19','2018-19 & 2019-20','2019-20 & 2020-21','2020-21 & 2021-22','2021-22 & 2022-23')''', [parquet])
summary = con.execute('''SELECT system, pooled_award_years AS period_label, COUNT(*) AS program_records, COUNT(earnings) AS numeric_earnings, COUNT(*) FILTER (WHERE EARN_MDN_1YR = 'PS') AS privacy_suppressed, COUNT(*) FILTER (WHERE EARN_MDN_1YR IS NULL OR TRIM(EARN_MDN_1YR) = '') AS blank, COUNT(*) FILTER (WHERE EARN_MDN_1YR IS NOT NULL AND TRIM(EARN_MDN_1YR) <> '' AND EARN_MDN_1YR <> 'PS' AND earnings IS NULL) AS other_nonnumeric, COUNT(*) FILTER (WHERE earnings <= 0) AS nonpositive, COUNT(*) FILTER (WHERE earnings < 20000) AS below_20000, COUNT(*) FILTER (WHERE earnings > 200000) AS above_200000, MIN(earnings) AS minimum, MAX(earnings) AS maximum FROM base GROUP BY 1,2 ORDER BY 1,2''').df()
summary.to_csv('one_year_earnings_summary.csv', index=False)
flags = con.execute('''SELECT system, INSTNM AS institution, CIPCODE AS program_code, CIPDESC AS program, CREDLEV AS credential, pooled_award_years AS period_label, earnings FROM base WHERE earnings < 20000 OR earnings > 200000 ORDER BY earnings''').df()
flags.to_csv('one_year_earnings_flagged.csv', index=False)
print(summary.to_string(index=False))
print('Saved summary and flagged records.')
