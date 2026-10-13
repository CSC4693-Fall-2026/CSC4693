from pathlib import Path

import pandas as pd

FINALIZATION_DIR = Path(__file__).resolve().parent.parent
DEPT_FILENAME = FINALIZATION_DIR / "Joining" / "csu_combined_updated.parquet"
PAY_FILENAME = FINALIZATION_DIR / "FilterFaculty" / "csu_faculty_2024.csv"

dept_df = pd.read_parquet(DEPT_FILENAME)

dept_df = dept_df[
    ~dept_df["name"].duplicated(keep="first")
].copy()

pay_df = pd.read_csv(PAY_FILENAME)

combined_df = pay_df.merge(
    dept_df,
    how = "inner",
    on = "name"
)

missing_df = pay_df[~pay_df["name"].isin(dept_df["name"])]


print(f"Combined records {len(combined_df)}")

print(f"Missing records {len(missing_df)}")

name_lst = missing_df["name"].tolist()
# unique_names = set(name_lst)
# dupes = []
# for name in unique_names:
#     name_lst.remove(name)
print(name_lst[500:700])

print(len(name_lst))

print(f"DPT Records: {len(dept_df)}")
print(f"Pay Records: {len(pay_df)}")

print("James Graham" in set(dept_df["name"].tolist()))

print("James Graham" in set(pay_df["name"].tolist()))

