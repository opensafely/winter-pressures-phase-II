import pandas as pd
from scipy import stats
import numpy as np

# Date specifications
study_start_date = "2022-01-03"

# Load and format data
measures = pd.read_csv("output/patient_measures/patient_measures.csv.gz")
# Reformat ethnicity data
# measures['ethnicity'].replace(
#    {1: 'White', 2: 'Mixed', 3: 'South Asian', 4: 'Black', 5: 'Other'},
#    inplace=True)
# measures['ethnicity'].fillna('Not Stated', inplace=True)
# Reformat rur_urb column
measures['rur_urb_class'].replace(
    {1: 'Urban major conurbation', 2: 'Urban minor conurbation', 3: 'Urban city and town', 
     4: 'Urban city and town in a sparse setting', 5: 'Rural town and fringe',
     6: 'Rural town and fringe in a sparse setting', 7: 'Rural village and dispersed',
     8: 'Rural village and dispersed in a sparse setting'},
    inplace=True)
measures['rur_urb_class'].fillna("Unknown", inplace = True)

# Create measure where: numerator = appt for disease X with prescription, denominator = appt for disease X
numerators = ["back_pain_opioid", "chest_inf_abx", "chest_inf_abx"]
denominators = ["back_pain", "chest_inf", "pneum"]

# List of column names to match the numerator-denominator pairs by
index = measures.columns.get_loc("age")
subgroups = list(measures.columns[index : ])
subgroups = subgroups + ["interval_start" , "interval_end"]

for numerator, denominator in zip(numerators, denominators):

    tmp_df = measures[measures['measure'].isin([numerator, denominator])]
    tmp_df = (tmp_df.groupby(subgroups)
              .apply(lambda group: pd.Series({
                  'measure': f'prop_{numerator}',
                  'numerator': group.loc[group['measure'] == numerator, 'numerator'].iloc[0],
                  'denominator': group.loc[group['measure'] == denominator, 'numerator'].iloc[0],
                  'ratio': group.loc[group['measure'] == numerator, 'numerator'].iloc[0] / 
                           group.loc[group['measure'] == denominator, 'numerator'].iloc[0]
              }))
              .reset_index())
    measures = pd.concat([measures, tmp_df], ignore_index=True)

# Save processed file
measures.to_csv("output/patient_measures/processed_patient_measures.csv.gz")

# Create practice-characteristics dataframe
practice_df = pd.read_csv("output/practice_measures/practice_measures.csv.gz")

# Reformat rur_urb column
practice_df['rur_urb_class'].replace(
    {1: 'Urban major conurbation', 2: 'Urban minor conurbation', 3: 'Urban city and town', 
     4: 'Urban city and town in a sparse setting', 5: 'Rural town and fringe',
     6: 'Rural town and fringe in a sparse setting', 7: 'Rural village and dispersed',
     8: 'Rural village and dispersed in a sparse setting'},
    inplace=True)
practice_df['rur_urb_class'].fillna("Unknown", inplace = True)

# Group measures by practice, using aggregate functions of interest
practice_df = (
    practice_df.groupby(["practice_pseudo_id", "interval_start"])
    .agg(
        numerator=("numerator", "sum"),
        list_size=("denominator", "sum"),
        count_female=("sex", lambda x: (x == "female").sum()),
        count_over_65=("age", lambda x: ((x == "adult<80") | (x == "adult>80")).sum()),
        count_under_5=("age", lambda x: (x == "preschool").sum()),
        median_imd=("imd_quintile", "median"),
        #count_ethnic=("ethnicity", lambda x: (x != 'White').sum()),
        mode_rur_urb=("rur_urb_class", lambda x: stats.mode(x).mode[0]),
    )
    .reset_index()
)

# Convert counts to percentages
cols_to_convert = ["count_female", "count_over_65", "count_under_5"
                   #, "count_ethnic"
                   ]
new_cols = ["pct_female", "pct_ovr_65", "pct_und_5"
            #, "pct_ethnic"
            ]
for index in range(0, len(cols_to_convert)):
    practice_df[new_cols[index]] = (
        practice_df[cols_to_convert[index]] / practice_df["list_size"]
    )

# Create column for numeric list size, used in standardization of rates
practice_df['list_size_raw'] = practice_df['list_size']
# Convert other numeric cols to quintiles
new_cols.append("list_size")
for col in new_cols:
    practice_df[col] = pd.qcut(practice_df[col], q=5, duplicates="drop")

practice_df.drop(columns=cols_to_convert, inplace=True)
practice_df.to_csv("output/practice_measures/processed_practice_measures.csv.gz")

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
