import os
import pandas as pd

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "data"

CSU_FILE = "golden_csu_2013-2024.parquet"
UC_FILE = "golden_uc_2013-2024.parquet"


def parquetToCSV(parquet_file : str) -> None:
    print(f"Writing '{parquet_file}' to csv...")
    filepath = os.path.join(CUR_DIR, DATA_DIR, "raw", parquet_file)

    df = pd.read_parquet(filepath)
    new_path = os.path.join(CUR_DIR, DATA_DIR, "new", parquet_file.replace("parquet", "csv")) 
    df.to_csv(new_path)
    print(f"Successfully written to '{new_path}'!")

def buildRollUp(csu_parquet : str, uc_parquet : str) -> None:
    print("Building roll up...")
    csu_df, uc_df = pd.read_parquet(
        os.path.join(CUR_DIR, DATA_DIR, "raw", csu_parquet)
    ), pd.read_parquet(
        os.path.join(CUR_DIR, DATA_DIR, "raw", uc_parquet)
    )
    rollup_df = pd.concat(
        [csu_df, uc_df],
        ignore_index=True,
    )

    output_path = os.path.join(
        CUR_DIR,
        DATA_DIR,
        "new",
        "golden_rollup_2013-2024.csv",
    )

    rollup_df.to_csv(output_path, index=False)

    print(f"Successfully created rollup at '{output_path}'!")


if __name__ == "__main__":

    # Convert parquets to CSV bc Tableau doesn't natively support parquets
    for file in [CSU_FILE, UC_FILE]:
        parquetToCSV(file)    

    # Concatenate both golden files
    buildRollUp(CSU_FILE, UC_FILE)



