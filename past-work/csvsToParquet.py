import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSU_DIR = ROOT / "processing/faculty/csu/output"
UC_DIR = ROOT / "processing/faculty/uc/output"
CSU_FAC = CSU_DIR / "csu_faculty_2024.csv"
UC_FAC = UC_DIR / "uc_faculty_2024.csv"

csu_df = pd.read_csv(CSU_FAC)
uc_df = pd.read_csv(UC_FAC)

csu_df.to_parquet(
    CSU_DIR / "csu_faculty_2024.parquet",
    index = False
)

uc_df.to_parquet(
    UC_DIR / "uc_faculty_2024.parquet",
    index = False
)
