"""
This script takes College Scorecard Graduate Earnings data
and removes all records including non-California Schools.
It also removes many columns that we are not interested in.
"""

import pandas as pd

ca_schools = set()

with open("Steel Thread/graduate_data/ca_universities", "r") as f:
    for name in f:
        ca_schools.add(name.strip().replace(", ", "-"))
print(f"CA Schools:\n{ca_schools}")

df = pd.read_csv("Steel Thread/graduate_data/Most-Recent-Cohorts-Field-of-Study.csv")

print(df.keys())

ca_df = df[df["INSTNM"].isin(ca_schools) ]

ca_df = ca_df.drop(columns=df.columns[
    df.columns.get_loc("DEBT_ALL_STGP_ANY_N"):
    df.columns.get_loc("EARN_COUNT_NWNE_5YR")
])

print(f"Includes {len(ca_df['INSTNM'].unique())} colleges")

ca_df.to_csv("Steel Thread/for_analysis/ca_collegescore.csv", index=False)