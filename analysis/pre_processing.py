# This script processes the raw measures output to generate patient-characteristic stratified measures
# Option --comorbid_measures flag to aggregate by comorbidities
# Option --demograph_measures flag to aggregate by demographics
# Option --practice_measures flag to aggregate by practice
# Option --test flag to run a lightweight test with a single date

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

if args.comorbid_measures:
    group = 'comorbid'  
    dtype_dict = {
    'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
    'denominator' : 'int64', 'age' : 'category', 'comorbid_chronic_resp' : 'bool', 'comorbid_copd': 'bool',
    'comorbid_asthma': 'bool', 'comorbid_dm': 'bool', 'comorbid_htn': 'bool', 'comorbid_immuno': 'bool', 'vax_flu_12m': 'bool',
    'vax_covid_12m': 'bool', 'vax_pneum_12m': 'bool'
    }    
elif args.demograph_measures:
    group = 'demograph'
    dtype_dict = {
        'measure': 'category', 'interval_start' : 'category', 'numerator' : 'int64', 
        'denominator' : 'int64', 'age' : 'category', 'sex' : 'category', 'ethnicity' : 'string', 
        'ethnicity_sus': 'string', 'imd_quintile' : 'int8', 'carehome' : 'category',
        'region' : 'category', 'rur_urb_class' : 'string', 
    }
elif args.practice_measures:
    group = 'practice'
    dtype_dict = {
    "measure": "category",
    "interval_start": "category",
    "numerator": "int64",
    "denominator": "int64",
    "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
    }

# Select columns to read
needed_cols = list(dtype_dict.keys())

# -------- Patient measures processing ----------------------------------

df_list = []
log_memory_usage(label="Before loading data")
# Load and format data for each interval
for date in dates:

    print(f"Loading {group} measures {date}", flush=True)
    input_path = f"output/{group}_measures/{group}_measures_{date}"
    output_path = f"output/{group}_measures/proc_{group}_measures"
    # Read in measures
    df = read_write(read_or_write = 'read', test = args.test, path = input_path, 
                dtype=dtype_dict, true_values=["T"], false_values=["F"], usecols=needed_cols)
    log_memory_usage(label=f"After loading measures {date}")
    print(f"Initial shape of input: {df.shape}", flush=True)
        
    # Rename denominator column to list_size
    df.rename(columns={'denominator': 'list_size'}, inplace=True)
    print(f"Data types of input: {df.dtypes}", flush=True)
    nan_counts = df.isna().sum()
    print(f"""Number of NA's in each columns {nan_counts}\n
            count without 0 numerator: {df[(df['numerator'] > 0)].shape}\n
            count without nan numerator: {df[(df['numerator'].notna())].shape}\n
            count without 0 list_size: {df[(df['list_size'] > 0)].shape}\n
            count without nan list_size: {df[(df['list_size'].notna())].shape}""", flush=True)
    
    # Drop rows with 0 list_size or nan list_size
    df = df[(df['list_size'] > 0) & (df['list_size'].notna())]
    print(f"After dropping rows with 0 list_size or nan list_size shape: {df.shape}", flush=True)

    df_list.append(df)
    del(df)
    log_memory_usage(label=f"After deletion of df")

# Save Concatenate yearly intervals into a single dataframe
proc_df = pd.concat(df_list)
del df_list
print(f"Data types of input: {proc_df.dtypes}", flush=True)
log_memory_usage(label=f"After deletion of dataframes")

if args.demograph_measures:
    # Replace numerical values with string values
    proc_df = replace_nums(proc_df, replace_ethnicity=True, replace_rur_urb=True)
    
# Save processed file
read_write(df = proc_df, read_or_write = 'write', test = args.test, path = output_path)