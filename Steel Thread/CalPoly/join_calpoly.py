import pandas as pd

salaries_df = pd.read_csv("./CSU_Data/california-state-university-salary-2024.csv")
faculty_df = pd.read_csv("./CalPoly/calpoly_faculty.csv")

# Create Name first
faculty_df["Name"] = (
    faculty_df["First Name"].fillna("").str.strip()
    + " "
    + faculty_df["Middle Initial"].fillna("").str.strip()
    + " "
    + faculty_df["Last Name"].fillna("").str.strip()
).str.replace(r"\s+", " ", regex=True).str.strip()

# Remove the now-unneeded name parts
faculty_df = faculty_df.drop(
    columns=["First Name", "Middle Initial", "Last Name"]
)

# Put faculty columns in your preferred order
faculty_df = faculty_df[["Name","Year Hired","Major","Position","Education"]]

merged_df = faculty_df.merge(
    salaries_df,
    how="inner",
    left_on="Name",
    right_on="name"
).drop(columns=["name"])

# Put Name first; keep all remaining salary columns afterward
cols = ["Name"] + [col for col in merged_df.columns if col != "Name"]
merged_df = merged_df[cols]

# Filter jobs
filtered_df = merged_df[
    merged_df["job"].str.contains(r"lecturer|instruct", case=False, na=False)
]

# Filter totalpay
filtered_df["totalpay"] = pd.to_numeric(filtered_df["totalpay"], errors="coerce")
filtered_df = filtered_df[filtered_df["totalpay"] != 0]

filtered_df.to_csv("for_analysis/calpoly_salary_data.csv", index=False)