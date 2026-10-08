import pandas as pd

CSU_FAC = "Finalization/FilterFaculty/csu_faculty_2024.csv"
UC_FAC = "Finalization/FilterFaculty/uc_faculty_2024.csv"

csu_df = pd.read_csv(CSU_FAC)
uc_df = pd.read_csv(UC_FAC)

csu_df.to_parquet(
    "Finalization/FilterFaculty/csu_faculty_2024.parquet",
    index = False
)

uc_df.to_parquet(
    "Finalization/FilterFaculty/uc_faculty_2024.parquet",
    index = False
)