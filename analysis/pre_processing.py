import pandas as pd
from scipy import stats
import numpy as np

# Date specifications
study_start_date = "2022-01-03"

# Load and format data
measures = pd.read_csv("output/patient_measures/winter_pressure_measures.csv.gz")
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
measures.to_csv("output/patient_measures/processed_measures.csv.gz")

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
        count_ethnic=("ethnicity", lambda x: (x != 'White').sum()),
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
practice_df.to_csv("output/practice_measures/practice_measures.csv.gz")

# Create frequency table
measures_at_start = measures[(measures['interval_start'] == study_start_date) & (measures['measure'] == 'appointments_in_interval')]
# Extract demographic variables
table_one_vars = measures.columns[measures.columns.get_loc('denominator') + 1:]
table_one = {}
# Iterate over all the demographic variables we want in table one
for var in table_one_vars:
    # Create an binary matrix composed of indicator variables representing the categorical value for each group (M)
    # Multiply this matrix by the vector of denominators representing the size of the given group (d)
    # Sum to get the total denominator value from all the groups (t = Sum(M x d))
    table_one[var] = pd.get_dummies(measures_at_start[var]).multiply(measures_at_start['denominator'], axis=0).sum().reset_index()
    table_one[var].columns = ['value', 'count']
    table_one[var]['prop'] = table_one[var]['count']/table_one[var]['count'].sum()

# Initialize an empty list to hold formatted DataFrames
formatted_list = []

# Loop over each item in the dictionary
for key, df in table_one.items():
    # Add a column for the category (e.g., age, sex, ethnicity)
    df['Category'] = key
    # Append the DataFrame to the list
    formatted_list.append(df[['Category', 'value', 'count', 'prop']])

# Concatenate all DataFrames into one
result_df = pd.concat(formatted_list, axis=0, ignore_index=True)
result_df.to_csv('output/patient_measures/frequency_table.csv', index=False)