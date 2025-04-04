#TODO:
# Update frequency table code at the end

import pandas as pd
from scipy import stats
import numpy as np
import argparse
from datetime import datetime, timedelta
import os
from utils import generate_annual_dates, log_memory_usage, replace_nums
import pyarrow.feather as feather
from wp_config_setup import *

# -------- Set up variables ----------------------------------

if test == True:
    dates = ["2016-08-10"]
    suffix = "_test"
else:
    dates = generate_annual_dates(2016, '2024-07-31')
    suffix = ""
study_start_date = dates[0]

log_memory_usage(label="Before loading data")

# -------- Patient measures processing ----------------------------------

patient_dataframes = []

# Load and format data for each interval
for date in dates:
    if comorbid:
        dtype_dict = {
        'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
        'denominator' : 'int64', 'age' : 'category', 'comorbid_chronic_resp' : 'bool', 'comorbid_copd': 'bool',
        'comorbid_asthma': 'bool', 'comorbid_dm': 'bool', 'comorbid_htn': 'bool', 'comorbid_immuno': 'bool', 'vax_flu_12m': 'bool',
        'vax_covid_12m': 'bool', 'vax_pneum_12m': 'bool'
        #'comorbid_depres': 'bool', 'comorbid_mh': 'bool', 'comorbid_neuro': 'bool',
        }    
    else:
        dtype_dict = {
            'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
            'denominator' : 'int64', 'age' : 'category', 'sex' : 'category', 'ethnicity' : 'object', 'imd_quintile' : 'int8', 'carehome' : 'category',
            'region' : 'category', 'rur_urb_class' : 'object', 
        }
    needed_cols = list(dtype_dict.keys())
    # Load data for each interval
    df = pd.read_csv(f"output/patient_measures/patient_measures_{date}{suffix}.csv.gz",
                                        dtype=dtype_dict, true_values=["T"], false_values=["F"], usecols=needed_cols)
    
    log_memory_usage(label=f"After loading patient {date}")
        
    if not comorbid:
        # Collapse rur_urb_class to two categories: #1 for urban and #2 for rural
        df['rur_urb_class'] = df['rur_urb_class'].apply(
            lambda x: '1' if x in ['1', '2', '3', '4'] else ('2' if x in ['5', '6', '7', '8'] else np.nan)
            )
    # print type of each column
    print(f"Data types of input: {df.dtypes}", flush=True)
    # Count NaNs in each column
    nan_counts = df.isna().sum()
    # Print result
    print(f"Number of NA's in each columns {nan_counts}", flush=True)
    print(f"Before grouping shape: {df.shape}", flush=True)
    # count without 0 numerator
    print(f"count without 0 numerator: {df[(df['numerator'] > 0)].shape}", flush=True)
    # count without nan numerator
    print(f"count without nan numerator: {df[(df['numerator'].notna())].shape}", flush=True)
    # count without 0 list_size
    print(f"count without 0 denominator: {df[(df['denominator'] > 0)].shape}", flush=True)
    # count without nan list_size
    print(f"count without nan denominator: {df[(df['denominator'].notna())].shape}", flush=True)

    # Perform efficient groupby and aggregation
    print('GROUPING AND AGGREGATING', flush=True)
    # Aggregate by the demographic columns
    groupby_cols = [col for col in needed_cols if col not in ['numerator', 'denominator']]
    df = df.groupby(groupby_cols).agg(
        numerator = ("numerator", "sum"),
        list_size=("denominator", "sum")
    ).reset_index()

    # count without 0 numerator
    print(f"count without 0 numerator: {df[(df['numerator'] > 0)].shape}", flush=True)
    # count without nan numerator
    print(f"count without nan numerator: {df[(df['numerator'].notna())].shape}", flush=True)
    # count without 0 list_size
    print(f"count without 0 list_size: {df[(df['list_size'] > 0)].shape}", flush=True)
    # count without nan list_size
    print(f"count without nan list_size: {df[(df['list_size'].notna())].shape}", flush=True)
    
    # Drop rows with 0 list_size or nan list_size
    df = df[(df['list_size'] > 0) & (df['list_size'].notna())]
    print(f"After grouping shape: {df.shape}", flush=True)

    print(f"After grouping: df.shape", flush=True)

    patient_dataframes.append(df)
    del(df)
    log_memory_usage(label=f"After deletion of patient df")

# Save processed file
patient_df = pd.concat(patient_dataframes)
del patient_dataframes
print(f"Data types of input: {patient_df.dtypes}", flush=True)
log_memory_usage(label=f"After deletion of patient_dataframes")

if not comorbid:
    # Replace numerical values with string values
    patient_df = replace_nums(patient_df, replace_ethnicity=True, replace_rur_urb=True)
    patient_file = ''
else:
    patient_file = '_comorbid'

# Save processed file
if test:
    patient_df.to_csv(f"output/patient_measures/proc_patient_measures_test{patient_file}.csv.gz")
else:
    feather.write_feather(patient_df, f"output/patient_measures/proc_patient_measures{patient_file}.arrow")

# -------- Frequency table generation ----------------------------------

# # Create frequency table
# patient_df_at_start = patient_df[(patient_df['interval_start'] == study_start_date) & (patient_df['measure'] == 'seen_in_interval')]
# # Extract demographic variables
# table_one_vars = patient_df.columns[patient_df.columns.get_loc('denominator') + 1:]
# table_one = {}
# # Iterate over all the demographic variables we want in table one
# for var in table_one_vars:
#     # Create an binary matrix composed of indicator variables representing the categorical value for each group (M)
#     # Multiply this matrix by the vector of denominators representing the size of the given group (d)
#     # Sum to get the total denominator value from all the groups (t = Sum(M x d))
#     table_one[var] = pd.get_dummies(patient_df_at_start[var]).multiply(patient_df_at_start['denominator'], axis=0).sum().reset_index()
#     table_one[var].columns = ['value', 'count']
#     table_one[var]['prop'] = table_one[var]['count']/table_one[var]['count'].sum()


# # Initialize an empty list to hold formatted DataFrames
# formatted_list = []

# # Loop over each item in the dictionary
# for key, df in table_one.items():
#     # Add a column for the category (e.g., age, sex, ethnicity)
#     df['Category'] = key
#     # Append the DataFrame to the list
#     formatted_list.append(df[['Category', 'value', 'count', 'prop']])

# # Concatenate all DataFrames into one
# result_df = pd.concat(formatted_list, axis=0, ignore_index=True)

# # Save processed file
# result_df.to_csv(f'output/patient_measures/frequency_table{suffix}.csv', index=False)
