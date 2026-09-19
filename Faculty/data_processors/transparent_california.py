# Lossless data processing for provided downloaded from Transparent Califronia

import polars as pl

def main():
    print("Scanning CSV files...")
    
    # Numerical cols
    financial_cols = [
        "base", "overtime", "other", "totalpay", "totalbenefits", 
        "totalpaybenefits"
    ]
    
    df = pl.scan_csv(
        "../data/raw/**/*.csv",
        include_file_paths="filepath"
    )
    # Empty Cols
    df = df.drop(['ual', 'benefitsee', 'benefitser', 'benefitsdc'], strict=False)
    
    # Helper function to currency text into Ints!
    def clean_currency(col_name):
        return ( pl.col(col_name) .cast(pl.Int32, strict=False))
        
    df = df.rename(str.lower)
    
    # Apply typing and data transformations
    df = df.with_columns(
        pl.selectors.string().str.to_lowercase()
    ).with_columns(
        # Get Year From Filename
        pl.col("filepath").str.extract(r"-(\d{4})\.csv$", 1).cast(pl.Int16).alias("year"),
        
        # Categorical cols
        pl.col("job").cast(pl.Categorical),
        pl.col("department").cast(pl.Categorical),
        
        # Clean and cast all financial columns
        *[clean_currency(col) for col in financial_cols]
    )
    
    df = df.drop(["filepath"])
    
    final_df = df.collect()
    final_df.write_parquet("../data/faculty-salaries.parquet", compression="zstd")
        
    print(f"Processed {final_df.height:,} records.")
    schema = final_df.schema
    for col_name, dtype in schema.items():
        print(f"{col_name}: {dtype}")

if __name__ == "__main__":
    main()