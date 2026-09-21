# Lossless data processing for the UC Faculty Dataset provided by a CPRA request to the UC System

import polars as pl

def main():
    print("Scanning xlsx files...")
    
    
    df_dict = pl.read_excel("../data/raw/**/*.xlsx",sheet_id=0)
    df = pl.concat(df_dict.values())
    df = df.rename(str.lower)
    
    df = df.with_columns(
        pl.selectors.string().str.to_lowercase()
    ).with_columns(
        # Since we just have year I figure datetime obj isnt worth it
        pl.col('year').cast(pl.Int16),
        
        # Change ints
        pl.col('base_pay').cast(pl.Int32),
        pl.col('overtime_pay').cast(pl.Int32),
        pl.col('other_pay').cast(pl.Int32),
        pl.col('gross_pay').cast(pl.Int32),

        
        # Cast to Categorical
        pl.col('campus').cast(pl.Categorical),
        pl.col('department').cast(pl.Categorical),
    )
    
    
    df.write_parquet("../data/uc-faculty.parquet")
    
    print(f"Processed {df.height:,} records.")
    schema = df.schema
    for col_name, dtype in schema.items():
        print(f"{col_name}: {dtype}")
    

if __name__ == "__main__":
    main()