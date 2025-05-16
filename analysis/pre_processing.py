# This script processes the raw measures output to generate patient-characteristic stratified measures
# Option --comorbid_measures flag to aggregate by comorbidities
# Option --demograph_measures flag to aggregate by demographics
# Option --practice_measures flag to aggregate by practice
# Option --test flag to run a lightweight test with a single date

#TODO:
# Update frequency table code at the end
# Check rural urb class is defined properly

import pandas as pd
from scipy import stats
import numpy as np
import argparse
from datetime import datetime, timedelta
import os
from utils import *
import pyarrow.feather as feather
from wp_config_setup import args

# --------- Configuration ------------------------------------------------

dates = generate_annual_dates(args.study_start_date, args.n_years)

if args.test:
    # Set test mode to use only the first year
    dates = dates[:1]
    print(f"Test mode: using {dates}", flush=True)
# -------- Patient measures processing ----------------------------------

df_list = []
log_memory_usage(label="Before loading data")
# Load and format data for each interval
for date in dates:
    if args.comorbid_measures:
        print("Loading comorbid measures", flush=True)
        # Define comorbid col datatypes
        dtype_dict = {
        'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
        'denominator' : 'int64', 'age' : 'category', 'comorbid_chronic_resp' : 'bool', 'comorbid_copd': 'bool',
        'comorbid_asthma': 'bool', 'comorbid_dm': 'bool', 'comorbid_htn': 'bool', 'comorbid_immuno': 'bool', 'vax_flu_12m': 'bool',
        'vax_covid_12m': 'bool', 'vax_pneum_12m': 'bool'
        }    
        input_path = f"output/comorbid_measures/comorbid_measures_{date}"
        output_path = "output/comorbid_measures/proc_comorbid_measures"

    elif args.demograph_measures:
        print("Loading demographic measures", flush=True)
        # Define demographic col datatypes
        dtype_dict = {
            'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
            'denominator' : 'int64', 'age' : 'category', 'sex' : 'category', 'ethnicity' : 'string', 
            'ethnicity_sus': 'string', 'imd_quintile' : 'int8', 'carehome' : 'category',
            'region' : 'category', 'rur_urb_class' : 'string', 
        }
        input_path = f"output/demograph_measures/demograph_measures_{date}"
        output_path = "output/demograph_measures/proc_demograph_measures"
    
    elif args.practice_measures:
        print("Loading practice measures", flush=True)
        
        dtype_dict = {
        "measure": "category",
        "interval_start": "category",
        "numerator": "int64",
        "denominator": "int64",
        "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
        }

        needed_cols = ['measure', 'interval_start', 'numerator', 'denominator','practice_pseudo_id']
        input_path = f"output/practice_measures/practice_measures_{date}"
        output_path = "output/practice_measures/proc_practice_measures"

    # Select columns to read
    needed_cols = list(dtype_dict.keys())
    # Read in measures
    df = read_write(read_or_write = 'read', test = args.test, path = input_path, 
                dtype=dtype_dict, true_values=["T"], false_values=["F"], usecols=needed_cols)
    log_memory_usage(label=f"After loading measures {date}")
    print(f"Initial shape of input: {df.shape}", flush=True)
        
    # Rename denominator column to list_size
    df.rename(columns={'denominator': 'list_size'}, inplace=True)
    print(f"Data types of input: {df.dtypes}", flush=True)
    nan_counts = df.isna().sum()
    print(f"Number of NA's in each columns {nan_counts}", flush=True)
    print(f"count without 0 numerator: {df[(df['numerator'] > 0)].shape}", flush=True)
    print(f"count without nan numerator: {df[(df['numerator'].notna())].shape}", flush=True)
    print(f"count without 0 list_size: {df[(df['list_size'] > 0)].shape}", flush=True)
    print(f"count without nan list_size: {df[(df['list_size'].notna())].shape}", flush=True)
    
    # Drop rows with 0 list_size or nan list_size
    df = df[(df['list_size'] > 0) & (df['list_size'].notna())]
    print(f"After dropping rows with 0 list_size or nan list_size shape: {df.shape}", flush=True)

    df_list.append(df)
    del(df)
    log_memory_usage(label=f"After deletion of df")

# Save processed file
proc_df = pd.concat(df_list)
del df_list
print(f"Data types of input: {proc_df.dtypes}", flush=True)
log_memory_usage(label=f"After deletion of dataframes")

if args.demograph_measures:
    # Replace numerical values with string values
    proc_df = replace_nums(proc_df, replace_ethnicity=True, replace_rur_urb=True)
    
# Save processed file
read_write(df = proc_df, read_or_write = 'write', test = args.test, path = output_path)

# -------- Frequency table generation ----------------------------------

# # Create frequency table
# proc_df_at_start = proc_df[(proc_df['interval_start'] == study_start_date) & (proc_df['measure'] == 'seen_in_interval')]
# # Extract demographic variables
# table_one_vars = proc_df.columns[proc_df.columns.get_loc('denominator') + 1:]
# table_one = {}
# # Iterate over all the demographic variables we want in table one
# for var in table_one_vars:
#     # Create an binary matrix composed of indicator variables representing the categorical value for each group (M)
#     # Multiply this matrix by the vector of denominators representing the size of the given group (d)
#     # Sum to get the total denominator value from all the groups (t = Sum(M x d))
#     table_one[var] = pd.get_dummies(proc_df_at_start[var]).multiply(proc_df_at_start['denominator'], axis=0).sum().reset_index()
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
