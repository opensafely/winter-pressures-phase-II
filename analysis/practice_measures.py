import pandas as pd
from scipy import stats
import numpy as np

# Load and format data
measures = pd.read_csv("output/dataset_measures.csv.gz")
# Reformat ethnicity data
measures['ethnicity'].replace(
    {1: 'White', 2: 'Mixed', 3: 'South Asian', 4: 'Black', 5: 'Other'},
    inplace=True)
measures['ethnicity'].fillna('Not Stated', inplace=True)
# Reformat rur_urb column
measures['rur_urb_class'].replace(
    {1: 'Urban major conurbation', 2: 'Urban minor conurbation', 3: 'Urban city and town', 
     4: 'Urban city and town in a sparse setting', 5: 'Rural town and fringe',
     6: 'Rural town and fringe in a sparse setting', 7: 'Rural village and dispersed',
     8: 'Rural village and dispersed in a sparse setting'},
    inplace=True)
measures.to_csv("output/processed_measures.csv.gz")

# Create practice-characteristics dataframe
practice_df = measures.copy()

# Group measures by practice, using aggregate functions of interest
practice_df = (
    measures.groupby(["practice_pseudo_id", "interval_start"])
    .agg(
        numerator=("numerator", "sum"),
        list_size=("denominator", "sum"),
        count_female=("sex", lambda x: (x == "female").sum()),
        count_over_65=("age", lambda x: ((x == "retired") | (x == "elderly")).sum()),
        count_under_5=("age", lambda x: (x == "preschool").sum()),
        median_imd=("imd_quintile", "median"),
        count_ethnic=("ethnicity", lambda x: (x != 1).sum()),
        mode_rur_urb=("rur_urb_class", lambda x: stats.mode(x).mode[0]),
    )
    .reset_index()
)

# Convert counts to percentages
cols_to_convert = ["count_female", "count_over_65", "count_under_5", "count_ethnic"]
new_cols = ["pct_female", "pct_ovr_65", "pct_und_5", "pct_ethnic"]
for index in range(0, len(cols_to_convert)):
    practice_df[new_cols[index]] = (
        practice_df[cols_to_convert[index]] / practice_df["list_size"]
    )

# Convert numeric cols to quintiles
new_cols.append("list_size")
for col in new_cols:
    practice_df[col] = pd.qcut(practice_df[col], q=5, duplicates="drop")

practice_df.drop(columns=cols_to_convert, inplace=True)
practice_df.to_csv("output/practice_measures.csv.gz")

# Create frequency table
measures_at_start = measures[measures['interval_start'] == '2022-01-03']
table_one_vars = ['age','sex','ethnicity','imd_quintile','carehome',
                  'region','rur_urb_class','vax_flu_12m','vax_covid_12m']
table_one = {}
for var in table_one_vars:
    table_one[var] = (measures_at_start[var].value_counts(normalize=True)
                      .rename_axis(f'Value')
                      .reset_index(name='Propn'))
table_one = pd.concat(table_one)
table_one.to_csv('output/frequency_table.csv.gz')