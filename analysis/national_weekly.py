# This script generates a national, weekly time series of RSV_sensitive rates
# for sense checking with other work packages.

# python analysis/national_weekly.py

import json
import pandas as pd
from scipy import stats
import numpy as np
import argparse
from datetime import datetime, timedelta
import os
from utils import *
import pyarrow.feather as feather
from parse_args import config

INTERVAL_TO_TEST = "2023-04-03" # Action will need to be edited if this is edited
DISEASE_TO_TEST = "rsv_specific" # Action will need to be edited if this is edited

input_path = f"output/practice_measures_resp/practice_measures_{INTERVAL_TO_TEST}"
output_path = f"output/practice_measures_resp/national_weekly_{DISEASE_TO_TEST}_{INTERVAL_TO_TEST}"   
practice_weekly_df = read_write(read_or_write="read", path=input_path, dtype=config["dtype_dict"], test = False)

# -------------- Test cases -----------------------------

if config["test"]:

    # 1 - {DISEASE_TO_TEST} in {INTERVAL_TO_TEST} where 2 practices have counts of 10
    test_date = pd.Timestamp(INTERVAL_TO_TEST)
    test_practice_ids = practice_weekly_df["practice_pseudo_id"].unique()[:2]
    practice_weekly_df['numerator'] = np.where(
        (practice_weekly_df['measure'] == DISEASE_TO_TEST) &
        (pd.to_datetime(practice_weekly_df['interval_start']) == test_date) &
        (practice_weekly_df['practice_pseudo_id'].isin(test_practice_ids)),
        10,
        practice_weekly_df['numerator']
    )


# ------------- Aggregate rsv_sensitive measure to national level -------------------------

# Drop unnecessary columns and filter to RSV_sensitive measure
practice_weekly_df.drop(columns=["interval_end", "ratio"], inplace=True)
practice_weekly_df = practice_weekly_df[practice_weekly_df['measure'] == DISEASE_TO_TEST]

# Redefine categories of measure to avoid aggregation issues
practice_weekly_df['measure'] = practice_weekly_df['measure'].cat.set_categories([DISEASE_TO_TEST])

# Aggregate practice level data to national level
national_weekly_df = build_aggregate_df(practice_weekly_df, ['measure', 'interval_start'], {'numerator': 'sum', 'denominator': 'sum', 'practice_pseudo_id': 'nunique'})

# Post-aggregation column edits
national_weekly_df.rename(columns={'practice_pseudo_id': 'n_practices_week'}, inplace=True)
national_weekly_df['rate_per_1000'] = (national_weekly_df['numerator'] / national_weekly_df['denominator']) * 1000

print(national_weekly_df)
read_write(read_or_write="write", df=national_weekly_df, path=output_path, file_type="csv", test = False)

# ------------- Aggregate weekly to yearly -------------------------

# Count number of unique practices in the overall year.
# Use the first weekly denominator (week 1) as yearly list size to avoid
# inflating denominator by summing list sizes across weeks.
national_yearly_df = build_aggregate_df(practice_weekly_df, ['measure'], 
                                        {'numerator': 'sum', 'practice_pseudo_id': 'nunique'}, 
                                        initial_list_size = True)

# Post-aggregation column edits
national_yearly_df.rename(columns={'practice_pseudo_id': 'n_practices_year'}, inplace=True)
national_yearly_df['rate_per_1000'] = (national_yearly_df['numerator'] / national_yearly_df['list_size_initial']) * 1000
national_yearly_df['year_start'] = INTERVAL_TO_TEST

print(national_yearly_df)
read_write(read_or_write="write", df=national_yearly_df, path=f"{output_path}_yearly", file_type="csv", test = False)


# ----------- Test case outputs --------------------------

# Print test cases
if config["test"]:

    # 1 - numerator should be 20 for {DISEASE_TO_TEST} in {INTERVAL_TO_TEST}
    test_output = national_weekly_df[
        (national_weekly_df['measure'] == DISEASE_TO_TEST) &
        (national_weekly_df['interval_start'] == INTERVAL_TO_TEST)
    ]
    print(f"Test Output for {DISEASE_TO_TEST} in {INTERVAL_TO_TEST}:")
    print(test_output)
    assert test_output['numerator'].values[0] == 20

