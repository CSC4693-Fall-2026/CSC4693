import pandas as pd

CSU_FILENAME = "Finalization/FilterFaculty/california-state-university-salary-2024.csv"
CSU_OUTPUT = "Finalization/FilterFaculty/csu_faculty_2024.csv"

UC_FILENAME = "Finalization/FilterFaculty/university-of-california-salary-2024.csv"
UC_OUTPUT = "Finalization/FilterFaculty/uc_faculty_2024.csv"


def clean_names(df):
    # Split names into tokens
    name_tokens = df["name"].fillna("").str.strip().str.split()

    # Discard records with fewer than 2 tokens
    df = df[name_tokens.str.len() >= 2].copy()

    # Rebuild name as only "First Last"
    name_tokens = df["name"].str.strip().str.split()
    df["name"] = name_tokens.str[0] + " " + name_tokens.str[-1]

    # Ensure "name" is the first column
    df = df[
        ["name"] + [col for col in df.columns if col != "name"]
    ]

    return df


# --------------------
# CSU
# --------------------

csu_df = pd.read_csv(CSU_FILENAME)

csu_df = clean_names(csu_df)

csu_faculty_df = csu_df[
    csu_df["job"].str.contains(
        r"Instructional Faculty|Lecturer",
        case=False,
        na=False
    )
].copy()

# Remove records with base salary of 0
csu_faculty_df = csu_faculty_df[
    csu_faculty_df["base"] != 0
].copy()

# Remove ALL records whose cleaned name appears more than once
csu_faculty_df = csu_faculty_df[
    ~csu_faculty_df["name"].duplicated(keep=False)
].copy()


# --------------------
# UC
# --------------------

uc_df = pd.read_csv(UC_FILENAME)

uc_df = clean_names(uc_df)

uc_faculty_df = uc_df[
    uc_df["job"].str.contains(
        r"(?:^|[\s-])(?:Prof(?:essor)?|Lect(?:urer)?)(?=$|[\s-])",
        case=False,
        na=False,
        regex=True
    )
].copy()

# Remove records with base salary of 0
uc_faculty_df = uc_faculty_df[
    uc_faculty_df["base"] != 0
].copy()

# Remove ALL records whose cleaned name appears more than once
uc_faculty_df = uc_faculty_df[
    ~uc_faculty_df["name"].duplicated(keep=False)
].copy()


# --------------------
# Save
# --------------------

csu_faculty_df.to_csv(CSU_OUTPUT, index=False)
uc_faculty_df.to_csv(UC_OUTPUT, index=False)

print(f"\nSaved {len(csu_faculty_df)} records for CSU Faculty")
print(f"Saved {len(uc_faculty_df)} records for UC Faculty")