# TODO:
# Add datatype argument to read_csv if memory still fails
import pandas as pd
from scipy import stats
import numpy as np
import argparse
from datetime import datetime, timedelta
import os
from utils import generate_annual_dates, log_memory_usage, replace_nums
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

practice_df_dict = {}

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
    "ethnicity": "object", # nullable integer type (not 'I' not 'i')
    "imd_quintile": "int8", # range of int8 is -128 to 127
    "carehome": "category",
    "region": "category",
    "rur_urb_class": "object",
    "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
    }
    practice_df_dict[date] = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         true_values=["T"], false_values=["F"])
    # print type of each column
    print(practice_df_dict[date].dtypes)
    # Concatenate all DataFrames into one
    practice_df = pd.concat(practice_df_dict.values(), ignore_index=True)

    log_memory_usage(label=f"After loading practice {date}")

del practice_df_dict
log_memory_usage(label=f"After deletion of practices_dict")
# Replace numerical values with string values
practice_df = replace_nums(practice_df)

# Group measures by practice, using aggregate functions of interest
practice_df = (
    practice_df.groupby(["practice_pseudo_id", "interval_start", "measure"])
    .agg(
        numerator=("numerator", "sum"),
        list_size=("denominator", "sum"),
        count_female=("sex", lambda x: (x == "female").sum()),
        count_over_65=("age", lambda x: ((x == "adult_under_80") | (x == "adult_over_80")).sum()),
        count_under_5=("age", lambda x: (x == "preschool").sum()),
        median_imd=("imd_quintile", "median"),
        count_ethnic=("ethnicity", lambda x: (x != 'White').sum()),
        mode_rur_urb=("rur_urb_class", lambda x: x.mode()),
    )
    .reset_index()
)

# Convert counts to percentages
cols_to_convert = ["count_female", "count_over_65", "count_under_5"
                , "count_ethnic"
                ]
new_cols = ["pct_female", "pct_ovr_65", "pct_und_5"
            , "pct_ethnic"
            ]
for index in range(0, len(cols_to_convert)):
    practice_df[new_cols[index]] = (
        practice_df[cols_to_convert[index]] / practice_df["list_size"]
    )

# Create column for numeric list size, used in standardization of rates
practice_df['denominator'] = practice_df['list_size']
# Convert other numeric cols to quintiles
new_cols.append("list_size")
for col in new_cols:
    practice_df[col] = pd.qcut(practice_df[col], q=5, duplicates="drop")

practice_df.drop(columns=cols_to_convert, inplace=True)

# Save processed file
if test:
    practice_df.to_csv(f"output/practice_measures/proc_practice_measures_test.csv.gz")
else:
    practice_df.to_csv(f"output/practice_measures/proc_practice_measures.csv.gz")

