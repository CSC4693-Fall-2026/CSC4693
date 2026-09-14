import pandas as pd

df = pd.read_csv("Steel Thread/for_analysis/ca_collegescore.csv")

calpoly_df = df[df["INSTNM"] == "California Polytechnic State University-San Luis Obispo"]

calpoly_df.to_csv("Steel Thread/for_analysis/calpoly_scorecard.csv", index=False)