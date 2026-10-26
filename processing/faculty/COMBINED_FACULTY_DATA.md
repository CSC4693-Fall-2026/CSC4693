# Combined UC and CSU faculty-pay data

I combined the detailed UC and CSU pay files so later groups can work from one consistent schema. I kept the individual records, school, original department, shared department bucket, job title, and each pay field. I did not average or otherwise summarize the salaries in this step.

## Files used

- `cleaned_uc_salaries_with_buckets_2013-2024.parquet`
- `csu_depbucket_cleaned_joined_pay_2013-2024.parquet`

Both files cover 2013–2024 and use the same 11 department buckets. The combined file has 3,732,727 records: 3,660,661 from the UC data and 72,066 from the CSU data. The row-count check passed, so the combine step did not lose any records.

## Column matching

| Combined column | UC column | CSU column |
|---|---|---|
| `year` | `year` | `year_transparentCA` |
| `system` | added as `UC` | added as `CSU` |
| `school` | `campus` | `school` |
| `faculty_name` | combined `first_name` and `last_name` | `name` |
| `job_title` | `title_name` | `title` |
| `faculty_role` | `role` | `role` when available |
| `original_department` | `original_department` | `original_department` |
| `department` | `department` | `department` |
| `total_pay` | `gross_pay` | `total_pay` |
| `base_pay` | `base_pay` | `base_pay` |
| `overtime_pay` | `overtime_pay` | `overtime_pay` |
| `other_pay` | `other_pay` | `other_pay` |

`gross_pay` in the UC file and `total_pay` in the CSU file are the matching total-pay fields, so the combined version calls both `total_pay`. The original source filename is also stored in every row.

## One issue to fix

The current CSU pipeline in GitHub is written to output a `role` column, but the CSU Parquet supplied for this combine does not actually contain it. I left `faculty_role` blank for CSU rather than guessing from a different title field. The CSU job title is still included, and the script will automatically keep the CSU role values if the file is regenerated with that column.

The UC source includes staff and student-worker records as well as faculty roles. I kept them because the class decided to preserve role information early and choose filters later. The final report group can filter `faculty_role` once it settles which roles belong in each comparison.

## Outputs

- `combined_uc_csu_faculty_pay_2013-2024.parquet`: combined detailed data
- `combined_faculty_validation.csv`: row counts, date coverage, school counts, and missing fields by system
- `combined_faculty_bucket_counts.csv`: record counts for every system and department bucket
- `combine_uc_csu_faculty.py`: code that recreates all three outputs

Run the script with:

```bash
python processing/faculty/combine_uc_csu_faculty.py "path/to/USE THIS DATA" "path/to/output"
```
