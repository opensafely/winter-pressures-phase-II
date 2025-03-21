# TODO:
# Instead of loading all data at once, iterate over each date and process it
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
    "interval_start": "category",
    "interval_end": "category",
    "ratio": "float32",
    "numerator": "int64",
    "denominator": "int64",
    "age": "category",
    "sex": "category",
    "ethnicity": "object",
    "imd_quintile": "int8", # range of int8 is -128 to 127
    "carehome": "category",
    "region": "category",
    "rur_urb_class": "Int8", # nullable integer type (not 'I' not 'i')
    "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
    }
    df = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         dtype = dtype_dict, true_values=["T"], false_values=["F"])

    log_memory_usage(label=f"After loading practice {date}")

    # print type of each column
    print(f"Data types of input: {df.dtypes}")

    # Perform efficient groupby and aggregation
    df = (
        df.groupby(["measure", "interval_start", "interval_end"])
        .agg(
            numerator=("numerator", "sum"),
            list_size=("denominator", "sum"),
        )
    )

    print(f"Data types of output dataframe: {df.dtypes}")
    proc_dataframes.append(df)
    del df
        
# Save processed file
proc_df = pd.concat(proc_dataframes)
del proc_dataframes

if test:
    proc_df.to_csv("output/ungrouped_measures/proc_ungrouped_measures_test.csv.gz")
else:
    feather.write_feather(proc_df, f"output/ungrouped_measures/proc_ungrouped_measures_{date}.arrow")

