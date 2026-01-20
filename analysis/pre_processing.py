# This script processes the raw measures output to generate patient-characteristic stratified measures
# Usage python analysis/pre_processing.py
# Option --comorbid_measures/demograph_measures/practice_measures to choose which type of measures to process
# Option --test flag to run a lightweight test with a single date
# Option --set all/sro/resp to choose which set of measures to process

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

dates = generate_annual_dates(args.study_end_date, args.n_years)
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

if args.test:
    # For testing, use only one date
    dates = [args.test_start_date]

# -------- Patient measures processing ----------------------------------

df_list = []
log_memory_usage(label="Before loading data")
# Load and format data for each interval
for date in dates:

    print(f"Loading {args.group} measures {date}", flush=True)
    input_path = f"output/{args.group}_measures_{args.set}{args.appt_suffix}/{args.group}_measures_{date}"
    output_path = f"output/{args.group}_measures_{args.set}{args.appt_suffix}/proc_{args.group}_measures"
    # Read in measures
    df = read_write(read_or_write="read", path=input_path, dtype=args.dtype_dict)
    log_memory_usage(label=f"After loading measures {date}")
    print(f"Initial shape of input: {df.shape}", flush=True)

    # Rename denominator column to list_size
    df.rename(columns={"denominator": "list_size"}, inplace=True)
    print(f"Data types of input: {df.dtypes}", flush=True)
    nan_counts = df.isna().sum()
    print(
        f"""Number of NA's in each columns {nan_counts}\n
            count without 0 numerator: {df[(df['numerator'] > 0)].shape}\n
            count without nan numerator: {df[(df['numerator'].notna())].shape}\n
            count without 0 list_size: {df[(df['list_size'] > 0)].shape}\n
            count without nan list_size: {df[(df['list_size'].notna())].shape}""",
        flush=True,
    )

    # Drop rows with 0 list_size or nan list_size
    df = df[(df["list_size"] > 0) & (df["list_size"].notna())]
    print(
        f"After dropping rows with 0 list_size or nan list_size shape: {df.shape}",
        flush=True,
    )

    df_list.append(df)
    del df
    log_memory_usage(label=f"After deletion of df")

# Save Concatenate yearly intervals into a single dataframe
proc_df = pd.concat(df_list)
del df_list
print(f"Data types of input: {proc_df.dtypes}", flush=True)
log_memory_usage(label=f"After deletion of dataframes")

if args.demograph_measures:
    # Replace numerical values with string values
    proc_df = replace_nums(proc_df, replace_ethnicity=True, replace_rur_urb=True)


if args.test:
    np.random.seed(42)  # For reproducibility in testing
    # Increase numerator and list_size for testing of downstream functions
    proc_df["numerator"] = np.random.randint(0, 500, size=len(proc_df))
    proc_df["list_size"] = np.random.randint(500, 1000, size=len(proc_df))

    # Simulate extra data for downstream testing
    print(proc_df["interval_start"].unique())
    print("Simulating practice measures data for testing")

    n_weeks = 52 * 2

    # Generate extended rows by shifting weeks and randomizing values
    extended_rows = []
    for i in range(1, n_weeks + 1):
        df_copy = proc_df.copy()
        df_copy["interval_start"] = df_copy["interval_start"] + timedelta(weeks=i)
        df_copy["numerator"] = np.random.randint(0, 500, size=len(df_copy))
        df_copy["list_size"] = np.random.randint(500, 1000, size=len(df_copy))
        extended_rows.append(df_copy)

    # Combine original and simulated rows
    proc_df = pd.concat([proc_df] + extended_rows, ignore_index=True)

    # Sample 10 unique practice_pseudo_ids
    test_practices = pd.Series(proc_df["practice_pseudo_id"].unique()).sample(10)
    proc_df = proc_df[proc_df["practice_pseudo_id"].isin(test_practices)]

    # Set values in 'numerator' column to 0 for the selected rows to simulate real data missingness
    # Define mask for conditional rows
    mask = (proc_df["measure"] == "online_consult") & (
        proc_df["interval_start"] < "2016-11-30"
    )
    # Get indices that meet condition
    matching_indices = proc_df[mask].index
    proc_df.loc[matching_indices, "numerator"] = 0

    # Drop some rows to simulate real data missingness
    # Define mask for conditional rows
    mask = (proc_df["measure"] == "call_from_gp") & (
        proc_df["interval_start"] < "2016-11-30"
    )
    # Get indices that meet condition
    matching_indices = proc_df[mask].index
    # Drop rows
    proc_df = proc_df.drop(matching_indices)
    # Drop duplicates
    proc_df = pd.concat([proc_df] + extended_rows, ignore_index=True)
    proc_df = proc_df.drop_duplicates(
        subset=["practice_pseudo_id", "measure", "interval_start"]
    )

    print(proc_df.head())

# Remove intervals before the first summer reference period
proc_df = proc_df[proc_df["interval_start"] > "2016-05-31"]

# Remove practices with < 750 list size
if args.practice_measures:
    print(
        f"Number of practices before filtering: {proc_df['practice_pseudo_id'].nunique()}",
        flush=True,
    )
    proc_df = proc_df[(proc_df["list_size"] > 750)]
    print(
        f"Number of practices after filtering: {proc_df['practice_pseudo_id'].nunique()}",
        flush=True,
    )

# Save processed file
read_write(read_or_write="write", path=output_path, df=proc_df)
