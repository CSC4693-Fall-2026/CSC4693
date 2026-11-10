import os
import pandas as pd

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "data"

STU_ROLLUP = "complete_rollup.parquet"
FAC_ROLLUP = "combined_fac_rollup.parquet"


def parquetToCSV(parquet_file : str) -> None:
    print(f"Writing '{parquet_file}' to csv...")
    filepath = os.path.join(CUR_DIR, DATA_DIR, "raw", parquet_file)

    df = pd.read_parquet(filepath)
    new_path = os.path.join(CUR_DIR, DATA_DIR, "new", parquet_file.replace("parquet", "csv")) 
    df.to_csv(new_path)
    print(f"Successfully written to '{new_path}'!")

if __name__ == "__main__":

    # Convert parquets to CSV bc Tableau doesn't natively support parquets
    for file in [FAC_ROLLUP, STU_ROLLUP]:
        parquetToCSV(file)    



