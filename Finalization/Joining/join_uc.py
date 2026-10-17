import pandas as pd

FILENAME = "Finalization/Joining/uc_joined.parquet" # Work with the parquet file provided in the Google Drive alr

df = pd.read_parquet(FILENAME)
