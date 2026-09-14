import pandas as pd

df = pd.read_csv("Steel Thread\for_analysis\ca_collegescore.csv", "")

calpoly_df = df[df[INSTNM] == ""]