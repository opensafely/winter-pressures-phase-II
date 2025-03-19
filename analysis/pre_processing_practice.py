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
    "ethnicity": "object",
    "imd_quintile": "int8", # range of int8 is -128 to 127
    "carehome": "category",
    "region": "category",
    "rur_urb_class": "Int8", # nullable integer type (not 'I' not 'i')
    "practice_pseudo_id": "int16", # range of int16 is -32768 to 32767
    }
    practice_df_dict[date] = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         dtype = dtype_dict, true_values=["T"], false_values=["F"])

    log_memory_usage(label=f"After loading practice {date}")

# Concatenate all DataFrames into one
practice_df = pd.concat(practice_df_dict.values(), ignore_index=True)
# print type of each column
print(f"Data types of input: {practice_df.dtypes}")
log_memory_usage(label=f"Before deletion of practices_dict")
del practice_df_dict
log_memory_usage(label=f"After deletion of practices_dict")
# Replace numerical values with string values
practice_df = replace_nums(practice_df, replace_ethnicity=True, replace_rur_urb=False)
print(practice_df.head())

# Aggregate by practice and assign counts of each demographic group
practice_df = (
    practice_df.groupby(["practice_pseudo_id", "interval_start", "measure"]) #SHOULD THIS BE PER MEASURE??
    .agg(
        numerator=("numerator", "sum"),
        list_size=("denominator", "sum"),
        count_female=("denominator", lambda x: x.loc[practice_df["sex"] == "female"].sum()),
        count_over_65=("denominator", lambda x: x.loc[(practice_df["age"] == "adult_under_80") | (practice_df["age"] == "adult_over_80")].sum()),
        count_under_5=("denominator", lambda x: x.loc[practice_df["age"] == "preschool"].sum()),
        count_ethnic=("denominator", lambda x: x.loc[practice_df["ethnicity"] != 'White'].sum()),
        count_low_imd=("denominator", lambda x: x.loc[practice_df["imd_quintile"] <= 2].sum()), # low imd is 1-2
        count_rural=("denominator", lambda x: x.loc[practice_df["rur_urb_class"] >= 5].sum()), # rural is 5-8
        count_carehome=("denominator", lambda x: x.loc[practice_df["carehome"] == True].sum())
    )
    .reset_index()
)

# Standardize counts for each practice characteristic by list size
cols_to_convert = ["count_female", "count_over_65", "count_under_5"
                , "count_ethnic", "count_low_imd", "count_rural"
                ]
new_cols = ["pct_female", "pct_ovr_65", "pct_und_5"
            , "pct_ethnic", "pct_low_imd", "pct_rural"
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
    practice_df[f'{col}_quint'] = pd.qcut(practice_df[col], q=5, duplicates="drop")

practice_df.drop(columns=cols_to_convert, inplace=True)

print(f"Data types of output dataframe: {practice_df.dtypes}")

# Save processed file
if test:
    feather.write_feather(practice_df, "output/practice_measures/proc_practice_measures_test.arrow")
else:
    feather.write_feather(practice_df, "output/practice_measures/proc_practice_measures.arrow")

