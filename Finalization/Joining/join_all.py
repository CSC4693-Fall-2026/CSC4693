import pandas as pd

CSU = "Finalization/Joining/csu_joined.parquet"
UC = "Finalization/Joining/uc_joined.parquet"
OUTPUT = "Finalization/Joining/ca_joined.parquet"

csu_df = pd.read_parquet(CSU)
uc_df = pd.read_parquet(UC)

# Convert UC campus values into formal school names
uc_campus_crosswalk = {
    "berkeley": "University of California, Berkeley",
    "davis": "University of California, Davis",
    "irvine": "University of California, Irvine",
    "los angeles": "University of California, Los Angeles",
    "merced": "University of California, Merced",
    "riverside": "University of California, Riverside",
    "san diego": "University of California, San Diego",
    "san francisco": "University of California, San Francisco",
    "santa barbara": "University of California, Santa Barbara",
    "santa cruz": "University of California, Santa Cruz",
    "uc sf law": "University of California College of the Law, San Francisco"
}

csu_subset = csu_df.rename(columns={
    "job": "job_title",
    "department_y": "department",
    "base": "base_pay"
})[["school", "job_title", "department", "base_pay"]].copy()

uc_subset = uc_df.rename(columns={
    "campus": "school",
    "title_name": "job_title"
})[["school", "job_title", "department", "base_pay"]].copy()

# Apply the campus-name crosswalk
uc_subset["school"] = uc_subset["school"].str.strip().str.lower().map(
    uc_campus_crosswalk
)

faculty_df = pd.concat([csu_subset, uc_subset], ignore_index=True)

print(faculty_df.head())

print(len(faculty_df))
faculty_df.to_parquet(OUTPUT)
