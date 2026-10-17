import pandas as pd

SCORECARD = "Steel Thread/graduate_data/ca_collegescore.csv"
O_MAJOR = "Steel Thread/graduate_data/ca_majors.csv"

scorecard_df = pd.read_csv(SCORECARD)

top_100_majors = (
    scorecard_df
    .groupby(["CIPCODE", "CIPDESC"])
    .size()
    .sort_values(ascending=False)
    .head(100)
    .reset_index(name="count")
)

top_100_majors.to_csv(O_MAJOR, index=False)