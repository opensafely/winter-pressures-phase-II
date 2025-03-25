# TODO:

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
flags = ["practice_measures"]
study_start_date = dates[0]

log_memory_usage(label="Before loading data")

# -------- Practice measures processing ----------------------------------

# Initialize a list to store processed data
proc_dataframes = []

# Load and format data for each interval
for date in dates:

    dtype_dict = {
    "measure": "category",
    "interval_start": "category",
    "numerator": "int64",
    "denominator": "int64",
    "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
    }
    needed_cols = ['measure', 'interval_start', 'numerator', 'denominator','practice_pseudo_id']
    practice_df = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         dtype = dtype_dict, true_values=["T"], false_values=["F"], usecols = needed_cols)

    log_memory_usage(label=f"After loading practice {date}")

    # number of unique values in each column
    print(f"Number of unique values in each column: {practice_df.nunique()}", flush=True)

    # print type of each column
    print(f"Data types of input: {practice_df.dtypes}", flush=True)
    print(f"Before grouping shape: {practice_df.shape}", flush=True)
    # count without 0 numerator
    print(f"count without 0 numerator: {practice_df[(practice_df['numerator'] > 0)].shape}", flush=True)
    # count without nan numerator
    print(f"count without nan numerator: {practice_df[(practice_df['numerator'].notna())].shape}", flush=True)
    # count without 0 list_size
    print(f"count without 0 denominator: {practice_df[(practice_df['denominator'] > 0)].shape}", flush=True)
    # count without nan list_size
    print(f"count without nan denominator: {practice_df[(practice_df['denominator'].notna())].shape}", flush=True)

    # Perform efficient groupby and aggregation
    print('GROUPING AND AGGREGATING', flush=True)
    practice_df = (
        practice_df.groupby(["measure","interval_start","practice_pseudo_id"])
        .agg(
            numerator=("numerator", "sum"),
            list_size=("denominator", "sum"),
        )
        .reset_index()
    )

    # count without 0 numerator
    print(f"count without 0 numerator: {practice_df[(practice_df['numerator'] > 0)].shape}", flush=True)
    # count without nan numerator
    print(f"count without nan numerator: {practice_df[(practice_df['numerator'].notna())].shape}", flush=True)
    # count without 0 list_size
    print(f"count without 0 list_size: {practice_df[(practice_df['list_size'] > 0)].shape}", flush=True)
    # count without nan list_size
    print(f"count without nan list_size: {practice_df[(practice_df['list_size'].notna())].shape}", flush=True)

    # Drop rows with 0 list_size or nan list_size
    practice_df = practice_df[(practice_df['list_size'] > 0) & (practice_df['list_size'].notna())]
    print(f"After grouping shape: {practice_df.shape}", flush=True)
   
    print(f"Data types of output dataframe: {practice_df.dtypes}", flush=True)
    proc_dataframes.append(practice_df)
    del practice_df
        
# Save processed file
proc_df = pd.concat(proc_dataframes)
del proc_dataframes

if test:
    proc_df.to_csv("output/practice_measures/proc_practice_measures_test.csv.gz")
else:
    feather.write_feather(proc_df, f"output/practice_measures/proc_practice_measures.arrow")
