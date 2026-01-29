# This script aggregates the weekly counts into cumulative yearly counts.
# Differs from direct yearly measures outputs by not including demographic breakdowns.
# Instead, it has more accurate total counts by avoiding inclusion criteria issues.
# Run using python analysis/aggregate_weekly.py
# Option --comorbid_measures/demograph_measures/practice_measures to choose which type of measures to process
# Option --test flag to run a lightweight test with a single date
# Option --set all/sro/resp to choose which set of measures to process
# Option --yearly flag to process only yearly measures
# Option --weekly_agg to indicate that yearly measures are to be aggregated from weekly measures

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
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(config["study_end_date"], config["n_years"])
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

input_path = (
    f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}/proc_practice_measures_midpoint6"
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

    # 3 - COVID specific where all practices have list size = 100
    practice_interval_df['list_size_midpoint6'] = np.where(
        (practice_interval_df['measure'] == 'covid_specific'),
        100,
        practice_interval_df['list_size_midpoint6']
    )

# -------- Aggregate practice-weekly to practice-yearly ----------------------------------

practice_interval_df['year'] = practice_interval_df['interval_start'].dt.year

practice_yearly_df = build_aggregate_df(
    practice_interval_df,
    ["measure", "practice_pseudo_id", "year"],
    {"numerator_midpoint6": ["sum"]},
)

# For list size we want the value from the earliest interval in the year
list_size_df = (
    practice_interval_df
    .sort_values(by=["measure", "practice_pseudo_id", "year", "interval_start"])
    .drop_duplicates(subset=["measure", "practice_pseudo_id", "year"], keep="first")
    [["measure", "practice_pseudo_id", "year", "list_size_midpoint6"]]
    .rename(columns={"list_size_midpoint6": "list_size_midpoint6_first"})
)

# Merge earliest list size into practice-yearly frame
practice_yearly_df = practice_yearly_df.merge(
    list_size_df, on=["measure", "practice_pseudo_id", "year"], how="left"
)

# Identify practices with zero counts for the year
practice_yearly_df['zero_indicator'] = np.where(
    practice_yearly_df['numerator_midpoint6_sum'] == 0, 1, 0
)
# Calculate rates = (number of cases / practice list size at start of yr) * 1000
practice_yearly_df['rate_mp6'] = (
    practice_yearly_df['numerator_midpoint6_sum'] /
    practice_yearly_df['list_size_midpoint6_first']
) * 1000
print(practice_yearly_df.head())

# Save practice yearly outputs
output_path = (
    f"output/practice_measures_{config['set']}{config['appt_suffix']}{config['yearly_suffix']}/proc_practice_measures_midpoint6"
)

# Create directory for weekly agg results
Path(f"output/practice_measures_{config['set']}{config['appt_suffix']}{config['yearly_suffix']}").mkdir(parents=True, exist_ok=True)

# Rename columns to work with decile charts script
output_df = practice_yearly_df.rename(
    columns={
        'numerator_midpoint6_sum': 'numerator_midpoint6',
        'list_size_midpoint6_first': 'list_size_midpoint6',
        'year': 'interval_start'
    }
)
# Convert interval_start to datetime for decile charts script
output_df['interval_start'] = pd.to_datetime(output_df['interval_start'], format='%Y')
read_write("write", output_path, df = output_df, file_type = 'arrow')

# -------- Aggregate practice-yearly to national-yearly ----------------------------------

# Aggregate practice-yearly to national-yearly, summing the earliest practice list sizes
national_yearly_df= build_aggregate_df(
    practice_yearly_df,
    ["measure", "year"],
    {"numerator_midpoint6_sum": ["sum"], "list_size_midpoint6_first": ["sum"], "zero_indicator": ["sum", "count"]},
)

# Rename columns for clarity
national_yearly_df.rename(
    columns={
        'numerator_midpoint6_sum_sum': 'cum_sum_numerator_mp6',
        'list_size_midpoint6_first_sum': 'initial_national_list_size_mp6',
        'zero_indicator_count': 'n_practices',
        'zero_indicator_sum': 'n_practices_zero_rate'
    },
    inplace=True
)

# Recalculate rates = (total number of cases / national list size at start of yr) * 1000
national_yearly_df['rate_mp6'] = (
    national_yearly_df['cum_sum_numerator_mp6'] /
    national_yearly_df['initial_national_list_size_mp6']
) * 1000

# Calculate proportion of practices with zero counts
national_yearly_df['propn_prac_zero_rate'] = (
    national_yearly_df['n_practices_zero_rate'] /
    national_yearly_df['n_practices']
)

print(national_yearly_df.head())

# Save national yearly outputs
output_path = (
    f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['yearly_suffix']}/national_yearly_summary"
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
    assert test_output['cum_sum_numerator_mp6'].values[0] == 0
    assert test_output['rate_mp6'].values[0] == 0
    assert test_output['propn_prac_zero_rate'].values[0] == 1

    # 2 - Numerator > 0, List size > 0, Rate > 0, Proportion of practices with zero count = very low
    test_output = national_yearly_df[
        (national_yearly_df['measure'] == 'rsv_specific') &
        (national_yearly_df['year'] == 2024)
    ]
    print("Test Output for rsv_specific in 2024:")
    print(test_output)
    assert test_output['cum_sum_numerator_mp6'].values[0] > 0
    assert test_output['rate_mp6'].values[0] > 0
    assert test_output['propn_prac_zero_rate'].values[0] < 0.5

    # 3 - All practices have list size = 100 for covid_specific
    test_output = national_yearly_df[
        (national_yearly_df['measure'] == 'covid_specific')
    ]
    print("Test Output for covid_specific:")
    print(test_output)
    expected_list_size = (
        practice_yearly_df[
            practice_yearly_df['measure'] == 'covid_specific'
        ]['practice_pseudo_id'].nunique() * 100
    )
    assert test_output['initial_national_list_size_mp6'].values[0] == expected_list_size