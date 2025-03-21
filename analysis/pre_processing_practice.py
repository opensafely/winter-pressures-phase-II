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
    practice_df = pd.read_csv(f"output/practice_measures/practice_measures_{date}{suffix}.csv.gz",
                                         dtype = dtype_dict, true_values=["T"], false_values=["F"])

    log_memory_usage(label=f"After loading practice {date}")

    # print type of each column
    print(f"Data types of input: {practice_df.dtypes}")

    # Replace numerical values with string values
    practice_df = replace_nums(practice_df, replace_ethnicity=True, replace_rur_urb=False)
    print(practice_df.head())

    # Create boolean masks and multiply by denominator to get correct counts
    practice_df["denom_female"] = practice_df["denominator"] * (practice_df["sex"] == "female")
    practice_df["denom_over_65"] = practice_df["denominator"] * practice_df["age"].isin(["adult_under_80", "adult_over_80"])
    practice_df["denom_under_5"] = practice_df["denominator"] * (practice_df["age"] == "preschool")
    practice_df["denom_has_age"] = practice_df["denominator"] * practice_df["age"].notna()
    practice_df["denom_ethnic"] = practice_df["denominator"] * ((practice_df["ethnicity"] != "White") & practice_df["ethnicity"].notna())
    practice_df["denom_has_ethnicity"] = practice_df["denominator"] * practice_df["ethnicity"].notna()
    practice_df["denom_low_imd"] = practice_df["denominator"] * ((practice_df["imd_quintile"] <= 2) & practice_df["imd_quintile"].notna())
    practice_df["denom_has_imd"] = practice_df["denominator"] * practice_df["imd_quintile"].notna()
    practice_df["denom_rural"] = practice_df["denominator"] * ((practice_df["rur_urb_class"] >= 5) & practice_df["rur_urb_class"].notna())
    practice_df["denom_has_rural"] = practice_df["denominator"] * practice_df["rur_urb_class"].notna()
    practice_df["denom_carehome"] = practice_df["denominator"] * ((practice_df["carehome"] == True) & practice_df["carehome"].notna())
    practice_df["denom_has_carehome"] = practice_df["denominator"] * practice_df["carehome"].notna()

    # Perform efficient groupby and aggregation
    practice_df = (
        practice_df.groupby(["practice_pseudo_id", "interval_end", "measure"])
        .agg(
            numerator=("numerator", "sum"),
            list_size=("denominator", "sum"),
            count_female=("denom_female", "sum"),
            count_over_65=("denom_over_65", "sum"),
            count_under_5=("denom_under_5", "sum"),
            count_has_age=("denom_has_age", "sum"),
            count_ethnic=("denom_ethnic", "sum"),
            count_has_ethnicity=("denom_has_ethnicity", "sum"),
            count_low_imd=("denom_low_imd", "sum"),
            count_has_imd=("denom_has_imd", "sum"),
            count_rural=("denom_rural", "sum"),
            count_has_rural=("denom_has_rural", "sum"),
            count_carehome=("denom_carehome", "sum"),
            count_has_carehome=("denom_has_carehome", "sum"),
        )
        .reset_index()
    )

    # Standardize counts for each practice characteristic by list size
    standardize_col = {
        "count_female": "list_size",
        "count_over_65": "count_has_age",
        "count_under_5": "count_has_age",
        "count_ethnic": "count_has_ethnicity",
        "count_low_imd": "count_has_imd",
        "count_rural": "count_has_rural",
        "count_carehome": "count_has_carehome"
    }
    for col, denom in standardize_col.items():
        # Standardize col by non-null total size of col
        practice_df[col] = practice_df[col] / practice_df[denom]
        # Convert other numeric cols to quintiles
        practice_df[f'{col}_quint'] = pd.qcut(practice_df[col], q=5, duplicates="drop")
        # Replace 'count' with 'pct' in column name
        practice_df.rename(columns={col: col.replace("count", "pct")}, inplace=True)

    # Create column for numeric list size, used in standardization of rates
    practice_df['denominator'] = practice_df['list_size']    
    practice_df['list_size_quint'] = pd.qcut(practice_df['list_size'], q=5, duplicates="drop")

    print(f"Data types of output dataframe: {practice_df.dtypes}")
    proc_dataframes.append(practice_df)
    del practice_df
        
# Save processed file
proc_df = pd.concat(proc_dataframes)
del proc_dataframes

if test:
    proc_df.to_csv("output/practice_measures/proc_practice_measures_test.csv.gz")
else:
    feather.write_feather(proc_df, f"output/practice_measures/proc_practice_measures_{date}.arrow")

