# This script aggregates the weekly counts into cumulative yearly counts.
# Differs from direct yearly measures outputs by not including demographic breakdowns.
# Instead, it has more accurate total counts by avoiding inclusion criteria issues.
# Run using python analysis/aggregate_weekly.py
# Option --comorbid_measures/demograph_measures/practice_measures to choose which type of measures to process
# Option --test flag to run a lightweight test with a single date
# Option --set all/sro/resp to choose which set of measures to process
# Option --yearly flag to process only yearly measures

import pandas as pd
from utils import *
import pyarrow.feather as feather
from parse_args import *
import numpy as np
import random
from datetime import datetime, timedelta
from scipy import stats
from itertools import product
import pyarrow.feather as feather


# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(config["study_end_date"], config["n_years"])
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

input_path = (
    f"output/{config['group']}_measures_{config['set']}/proc_{config['group']}_measures_midpoint6"
)

practice_interval_df = read_write("read", input_path)

# -------------- Test cases -----------------------------

if config["test"]:

    # 1 - Specific_flu in 2023 with all practices having zero counts 
    practice_interval_df['numerator_midpoint6'] = np.where(
        (practice_interval_df['measure'] == 'flu_specific') &
        (practice_interval_df['interval_start'].dt.year == 2023),
        0,
        practice_interval_df['numerator_midpoint6']
    )

    # 2 - Specific RSV in 2024 with 1 practice with a rate of 0
    unique_practices = practice_interval_df['practice_pseudo_id'].unique()
    random_practice = random.choice(unique_practices.tolist())
    practice_interval_df['numerator_midpoint6'] = np.where(
        (practice_interval_df['measure'] == 'rsv_specific') &
        (practice_interval_df['interval_start'].dt.year == 2024) &
        (practice_interval_df['practice_pseudo_id'] == random_practice),
        0,
        practice_interval_df['numerator_midpoint6']
    )

# -------- Aggregate practice-weekly to practice-yearly ----------------------------------

practice_interval_df['year'] = practice_interval_df['interval_start'].dt.year

practice_yearly_df= build_aggregate_df(
    practice_interval_df,
    ["measure", "practice_pseudo_id", "year"],
    {"numerator_midpoint6": ["sum"], "list_size_midpoint6": ["sum"]},
)

# Identify practices with zero counts for the year
practice_yearly_df['zero_indicator'] = np.where(
    practice_yearly_df['numerator_midpoint6_sum'] == 0, 1, 0
)
print(practice_yearly_df.head())

# -------- Aggregate practice-yearly to national-yearly ----------------------------------

national_yearly_df= build_aggregate_df(
    practice_yearly_df,
    ["measure", "year"],
    {"numerator_midpoint6_sum": ["sum"], "list_size_midpoint6_sum": ["sum", "count"], "zero_indicator": ["sum"]},
)

# Recalculate rates
national_yearly_df['rate_midpoint6'] = (
    national_yearly_df['numerator_midpoint6_sum_sum'] /
    national_yearly_df['list_size_midpoint6_sum_sum']
) * 1000

# Calculate proportion of practices with zero counts
national_yearly_df['propn_prac_zero_rate'] = (
    national_yearly_df['zero_indicator_sum'] /
    national_yearly_df['list_size_midpoint6_sum_count']
)

print(national_yearly_df.head())

# Save national yearly outputs
output_path = (
    f"output/{config['group']}_measures_{config['set']}/national_yearly_summary"
)
read_write("write", output_path, df = national_yearly_df, file_type = 'csv')

# ----------- Test case outputs --------------------------

# Print test cases
if config["test"]:

    # 1 - Numerator = 0, List size > 0, Rate = 0, Proportion of practices with zero counts = 1
    test_output = national_yearly_df[
        (national_yearly_df['measure'] == 'flu_specific') &
        (national_yearly_df['year'] == 2023)
    ]
    print("Test Output for flu_specific in 2023:")
    print(test_output)
    assert test_output['numerator_midpoint6_sum_sum'].values[0] == 0
    assert test_output['rate_midpoint6'].values[0] == 0
    assert test_output['propn_prac_zero_rate'].values[0] == 1

    # 2 - Numerator > 0, List size > 0, Rate > 0, Proportion of practices with zero count = very low
    test_output = national_yearly_df[
        (national_yearly_df['measure'] == 'rsv_specific') &
        (national_yearly_df['year'] == 2024)
    ]
    print("Test Output for rsv_specific in 2024:")
    print(test_output)
    assert test_output['numerator_midpoint6_sum_sum'].values[0] > 0
    assert test_output['rate_midpoint6'].values[0] > 0
    assert test_output['propn_prac_zero_rate'].values[0] < 0.5