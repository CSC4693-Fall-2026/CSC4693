"""
This script calculates the median values for pay
and benefits across majors for CalPoly Faculty.
"""

import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent
df = pd.read_csv(HERE / "output/calpoly_salary_data.csv")

# Consider removing emeritus professors

df.drop(columns=["Name", "Year Hired", "Position", "Education", "job", "department"], inplace=True)

major_medians = (
    df.groupby("Major", as_index=False)
    .median(numeric_only=True)
)

major_medians.to_csv(HERE / "output/calpoly_major_medians.csv", index=False)
