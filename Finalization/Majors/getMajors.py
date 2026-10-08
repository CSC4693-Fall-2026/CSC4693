"""
We will establish a list of 100 majors that we will analyze.
We use a subset of all majors to maintain practicality.
We select our 100 majors based on the top 100 most popular
    majors according to IPEDS July 2022 - June 2023.
"""

import pandas as pd

IPEDS_FILENAME = "ipeds_awards_2023.xlsx"

ipeds_df = pd.read_excel(f"Finalization/Majors/{IPEDS_FILENAME}")

# Keep only CIP codes at the XX.XX hierarchy.
# Examples:
#   11.0    -> excluded
#   11.07   -> kept
#   11.0701 -> excluded
ipeds_df = ipeds_df[
    ipeds_df["CIPCODE"].astype(str).str.match(r"^\d{2}\.\d{2}$")
]

# Group all rows belonging to the same CIP code and sum
# the total number of degrees awarded.
major_counts = (
    ipeds_df
    .groupby("CIPCODE", as_index=False)["CTOTALT"]
    .sum()
)

# Sort majors from most to least popular.
major_counts = major_counts.sort_values(
    by="CTOTALT",
    ascending=False
)

# Select the top 100 majors.
top_100_majors = major_counts.head(100).reset_index(drop=True)

# Add an explicit ranking.
top_100_majors.insert(
    0,
    "Rank",
    range(1, len(top_100_majors) + 1)
)

print(top_100_majors)

# Save results.
top_100_majors.to_csv(
    "Finalization/Majors/top_100_majors.csv",
    index=False
)