import pandas as pd

measures = pd.read_csv("output/appointments/app_measures.csv")

# Creating a summary table of that aggregates the interval counts into total counts
summary_table = measures.groupby("measure").sum()[["numerator", "denominator"]].sort_values(by=['measure'], ascending=False)
summary_table.to_csv("output/appointments/app_summary.csv")