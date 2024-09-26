import pandas as pd

measures = pd.read_csv("output/appointments/app_measures.csv.gz")
summary_table = measures.groupby("measure").sum()[["numerator", "denominator"]].sort_values(by=['measure'], ascending=False)
summary_table.to_csv("output/appointments/app_summary.csv.gz")