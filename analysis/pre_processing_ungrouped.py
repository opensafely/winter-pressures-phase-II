# This script process the raw measures output to generate ungrouped measures 
# i.e. no practice or patient stratification. Developed as a reserve option
# due to memory issues when processing generating large, stratified datasets.
# Option --test flag to run a lightweight test with a single date

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

# -------- Unstratified measures processing ----------------------------------

# Initialize a list to store processed data
proc_dataframes = []

# Load and format data for each interval
for date in dates:

    dtype_dict = {
    "measure": "category",
    "interval_start": "object",
    "numerator": "int64",
    "denominator": "int64",
    }
    
    needed_cols = ['measure', 'interval_start', 'numerator', 'denominator']
    
    df = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         dtype = dtype_dict, true_values=["T"], false_values=["F"], usecols = needed_cols, parse_dates=["interval_start"])

    df['interval_start'] = df['interval_start'].dt.normalize()

    log_memory_usage(label=f"After loading {date}")

    # Print df info
    print(f"Data types of input: {df.dtypes}", flush=True)
    print(f"Before grouping shape: {df.shape}", flush=True)
    print(f"count without 0 numerator: {df[(df['numerator'] > 0)].shape}", flush=True)
    print(f"count without 0 denominator: {df[(df['denominator'] > 0)].shape}", flush=True)

    # Print time stamp
    print('GROUPING AND AGGREGATING', flush=True)

    # Perform groupby and aggregation
    df = (
        df.groupby(["measure", "interval_start"])
        .agg(
            numerator=("numerator", "sum"),
            list_size=("denominator", "sum"),
        )
    )

    # Print df aggregated info
    print(f"Data types of output: {df.dtypes}", flush=True)
    print(f"After grouping shape: {df.shape}", flush=True)
    print(f"count without 0 numerator: {df[(df['numerator'] > 0)].shape}", flush=True)
    print(f"count without 0 list_size: {df[(df['list_size'] > 0)].shape}", flush=True)
    
    proc_dataframes.append(df)
    del df
    log_memory_usage(label=f"After deletion of patient df")
        
# Save processed file
proc_df = pd.concat(proc_dataframes)
del proc_dataframes
log_memory_usage(label=f"After deletion of patient_dataframes")

if test:
    proc_df.to_csv("output/ungrouped_measures/proc_ungrouped_measures_test.csv.gz")
else:
    feather.write_feather(proc_df, f"output/ungrouped_measures/proc_ungrouped_measures.arrow")

