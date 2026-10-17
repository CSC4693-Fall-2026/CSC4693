import pandas as pd

FILE = "Finalization/Joining/ca_joined.parquet"

DEPTS = {
    "Engineering",
    "Computer Science",
    "Science & Mathematics",
    "Medicine & Health Sciences",
    "Business, Economics, & Finance",
    "Agriculture, Food, & Animal",
    "Architecture & Environmental Design",
    "Humanities & Languages",
    "Social Sciences & Communication",
    "Education & Public Administration",
    "Trade & Vocational Professions"
}

df = pd.read_parquet(FILE)

depts = df["department"].tolist()

new = set()
for d in depts:
    if not d in DEPTS:
        new.add(d)

print(new)
print(len(new))