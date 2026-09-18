import duckdb
from pathlib import Path


def main():
    # Not used, but this is how I stored the CSVs
    csu_csv = Path("CSC4693/Faculty/data/raw/gcc/2024_CaliforniaStateUniversity.csv")
    cc_csv = Path("CSC4693/Faculty/data/raw/gcc/2024_CommunityCollegeDistrict.csv")
    uc_csv = Path("CSC4693/Faculty/data/raw/gcc/2024_UniversityOfCalifornia.csv")
    
    
    gcc_parquet = Path("CSC4693/Faculty/data/GCC.parquet")
    if not gcc_parquet.is_file():
        # All faculty pay CSVs for CSU, CC, and UC can be cleanly combined into one
        duckdb.sql(f"""
            COPY (
                SELECT * FROM read_csv('CSC4693/Faculty/data/raw/gcc/*.csv', ignore_errors=true)
            ) TO '{gcc_parquet}'
        """)

if __name__ == "__main__":
    main()