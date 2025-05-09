# This script normalizes the practice measures data by calculating rate ratios and testing for seasonality.
# It also performs a long-term trend analysis on the rate ratios and rounded rates.
# Option --test flag to run a lightweight test using simulated data

#TODO:
# 1. Make .apply filtering more efficient
# 1. Check assumptions for poissoin
# 2. Add visualisation of rate ratios to deciles_chart.r

import pandas as pd
from utils import generate_annual_dates, log_memory_usage, replace_nums
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np
import random 
from datetime import datetime, timedelta
from scipy import stats
from itertools import product
import pyarrow.feather as feather

# -------- Load data ----------------------------------

if test == True:
    study_start_date = datetime.strptime("2019-08-10", "%Y-%m-%d")
    suffix = "_test"
else:
    dates = generate_annual_dates(2016, '2024-07-31')
    suffix = ""
    study_start_date = dates[0]

def compare_to_summer(row, max_year, min_year, max_year_issue, min_year_issue, diff, season_df):
    '''
    Calculates the difference between the rate and the summer baseline for a given measure and year.
    Args:
        row (pd.Series): Row of the DataFrame containing the measure, year, and rate.
        max_year (int): Maximum year in the dataset.
        min_year (int): Minimum year in the dataset.
        max_year_issue (bool): Whether the latest year has no summer. Prev year summer used instead.
        min_year_issue (bool): Whether the earliest year has no summer. Next year summer used instead.
        diff (str): Type of difference to calculate ('Abs', 'Rel', 'Both').
    Returns:
        float: The difference between the rate and the summer baseline.
    '''
    year = row['year']
    # Check if the year is the max or min year and if it has a summer
    if (year == max_year) and (max_year_issue):
        print(f'Interval {row.interval_start} does not have a summer for that year, using prev years')
        year = year - 1
    elif (year == min_year) and (min_year_issue):
        print(f'Interval {row.interval_start} does not have a summer for that year, using next years')
        year = year + 1
    else:
        print(f'Interval {row.interval_start} has a summer for that year')
    # Get the summer value for the measure and year
    summer_value = season_df.loc[(row['measure'], 'Jun-Jul', year)]['mean']
    # Calculate rate normalized by summer baseline
    if diff == 'Abs':
        # Calculate absolute difference
        return row.rate_per_1000 - summer_value
    elif diff == 'Rel':
        # Calculate relative difference
        return row.rate_per_1000 / summer_value
    elif diff == 'Both':
        # Calculate both absolute and relative difference
        return pd.Series({'rate_diff': row.rate_per_1000 - summer_value, 'RR': row.rate_per_1000 / summer_value})

def test_difference(row, rate_df):
    '''
    Conducts a poisson means test comparing the summer and winter rates for a given measure, season and practice.
    Args:
        row (pd.Series): Row of the DataFrame containing the measure, season, and practice.
        rate_df (pd.DataFrame): DataFrame containing the rate data. Should be interval-level.
    Returns:
        float: The p-value of the difference between summer and winter values.
    '''
    print(f"Testing difference for measure: {row['measure']}, season: {row['season']}, practice: {row['practice_pseudo_id']}")
    if row['season'] == 'Jun-Jul':
        print("Skipping summer-summer comparison")
        return np.nan
    # Extract the summer and winter values for the measure, season, and year
    summer = rate_df.loc[
        (rate_df['measure'] == row['measure']) &
        (rate_df['season'] == 'Jun-Jul') &
        (rate_df['practice_pseudo_id'] == row['practice_pseudo_id'])
        ]
    season = rate_df.loc[
        (rate_df['measure'] == row['measure']) &
        (rate_df['season'] == row['season']) &
        (rate_df['practice_pseudo_id'] == row['practice_pseudo_id'])
        ]
    # Get the rates for summer and winter
    vals_summer = summer['rate_per_1000']
    vals_season = season['rate_per_1000']
    
    # Conduct poisson test
    rate1 = round(vals_summer.sum())
    intervals1 = len(vals_summer)
    print(f"Rate summer: {rate1}, Intervals summer: {intervals1}")
    rate2 = round(vals_season.sum())
    intervals2 = len(vals_season)
    print(f"Rate season: {rate2}, Intervals season: {intervals2}")
    if intervals1 == 0 or intervals2 == 0:
        print("One of the counts is zero, returning NaN")
        return np.nan
    result = stats.poisson_means_test(rate1, intervals1, rate2, intervals2, alternative='two-sided')

    # Get the p-value
    pval = result.pvalue

    # Return significance at p < 0.05
    return round(pval, 4)

def get_season(month):
    '''
    Returns the season for a given month.
    Args:
        month (int): Month number (1-12).
    Returns:
        str: Season name (2 month period).
    '''
    if month in [9, 10]:
        return 'Sep-Oct'
    elif month in [11, 12]:
        return 'Nov-Dec'
    elif month in [1, 2]:
        return 'Jan-Feb'
    elif month in [6, 7]:
        return 'Jun-Jul'
    else:
        return None  # Exclude non-winter months

log_memory_usage(label="Before loading data")

# Load practice data
if test:
    # Generate simulated data
    # Parameters
    measures = ['CancelledbyPatient', 'CancelledbyUnit', 'DidNotAttend',
        'GP_ooh_admin', 'Waiting', 'call_from_gp', 'call_from_patient',
        'emergency_care', 'follow_up_app', 'online_consult',
        'secondary_referral', 'seen_in_interval', 'start_in_interval',
        'tele_consult', 'vax_app', 'vax_app_covid', 'vax_app_flu']

    # Define sample values
    practice_ids = range(1, 10)  # 3 practices
    # Generate 4 years worth of data (pre, during, and post-pandemic covered)
    dates = pd.date_range(start=study_start_date, periods=(52*4), freq='7D').strftime('%Y-%m-%d')  

    # Initialize list to collect rows
    rows = []

    # Iterative data generation
    for measure in measures:
        for practice_id in practice_ids:
            for i, date in enumerate(dates):
                rows.append({
                    'Unnamed: 0': 1,
                    'measure': measure,
                    'interval_start': date,
                    'practice_pseudo_id': practice_id,
                    'numerator': np.round(np.random.uniform(0, 50), 1),  # float64
                    'list_size': np.round(np.random.uniform(100, 1000), 1)  # float64
                })
        # Convert to DataFrame
    practice_interval_df = pd.DataFrame(rows)
else:
    practice_interval_df = feather.read_feather("output/practice_measures/proc_practice_measures.arrow")

log_memory_usage(label="After loading data")

# -------- Define useful variables ----------------------------------

# Ensure interval_start is datetime
practice_interval_df['interval_start'] = pd.to_datetime(practice_interval_df['interval_start'])
# Extract year
practice_interval_df['year'] = practice_interval_df['interval_start'].dt.year
practice_interval_df['month'] = practice_interval_df['interval_start'].dt.month
practice_interval_df['rate_per_1000'] = practice_interval_df['numerator'] / practice_interval_df['list_size'] * 1000
pandemic_conditions = [
    practice_interval_df['interval_start'] < pd.to_datetime("2020-03-01"),
        (practice_interval_df['interval_start'] >= pd.to_datetime("2020-03-01")) & 
        (practice_interval_df['interval_start'] <= pd.to_datetime("2021-03-17")),
    practice_interval_df['interval_start'] > pd.to_datetime("2021-03-17")
]
choices = ['pre', 'during', 'post'] 
practice_interval_df['pandemic'] = np.select(pandemic_conditions, choices)

# Remove interval containing xmas shutdown
practice_interval_df = practice_interval_df.loc[~(
                                (practice_interval_df['interval_start'].dt.month == 12) & 
                                    (
                                    (practice_interval_df['interval_start'].dt.day >= 19) &
                                    (practice_interval_df['interval_start'].dt.day <= 26)
                                    )
                                )
                            ]
practice_interval_df['season'] = practice_interval_df['month'].apply(get_season)

# Variables used for determining which summer to use as a baseline for a given interval
max_year = practice_interval_df['year'].max()
min_year = practice_interval_df['year'].min()
max_year_issue = practice_interval_df[practice_interval_df['year'] == max_year]['month'].max() <= 5
min_year_issue = practice_interval_df[practice_interval_df['year'] == min_year]['month'].min() >= 8

# Create smaller df, summarized at season level using mean
# This is used as a reference for the rate ratio calculation
season_df = practice_interval_df[practice_interval_df['season'].notnull()]
season_df = (
    season_df.groupby(['measure', 'season', 'year'])['rate_per_1000']
    .agg(['mean'])
)

# ----------------------- Seasonality analysis ----------------------------------

# Calculate rate ratio at for all intervals
practice_interval_df['RR'] = practice_interval_df.apply(compare_to_summer,
    axis=1,
    args=(max_year, min_year, max_year_issue, min_year_issue, 'Rel', season_df)
)
# Save rate ratios (essentially de-trended rates)
if test:
    practice_interval_df.to_csv('output/practice_measures/RR_test.csv')
else:
    feather.write_feather(practice_interval_df, 'output/practice_measures/RR.arrow')

# Filter for summer and winter
practice_interval_sum_win_df = practice_interval_df.loc[practice_interval_df['season'].isin(['Jun-Jul', 'Sep-Oct', 'Nov-Dec', 'Jan-Feb'])]

# Calculate rate difference at practice level 
practice_interval_sum_win_df['rate_diff'] = practice_interval_sum_win_df.apply(compare_to_summer,
    axis=1,
    args=(max_year, min_year, max_year_issue, min_year_issue, 'Abs', season_df)
)

# Test for seasonality at practice-measure-season-level
# Create practice-measure-season df
practices = practice_interval_sum_win_df['practice_pseudo_id'].unique()
measures = practice_interval_sum_win_df['measure'].unique()
seasons = practice_interval_sum_win_df['season'].unique()
combinations = list(product(practices, measures, seasons))
practice_sum_win_df = pd.DataFrame(combinations, columns=['practice_pseudo_id', 'measure', 'season'])
# Apply poisson means test to each practice-measure-season combination
practice_sum_win_df['test_summer_vs_winter'] = (
    practice_sum_win_df
    # Feed the interval-level df to the function
    .apply(test_difference, axis=1, args=(practice_interval_sum_win_df, ))
)
practice_sum_win_df['signif'] = practice_sum_win_df['test_summer_vs_winter'] < 0.05
# Calculate proportion of significant results at measure-season level
results = practice_sum_win_df.groupby(['measure', 'season']).agg({
    'signif': ['sum', 'count'],
}).reset_index().round(2)
# Fix column index
results.columns = ['_'.join(col).strip('_') for col in results.columns.values]

# Aggregate practice results to measure-season level, and calculate the sum and count of significant results
sum_win_df = practice_interval_sum_win_df.groupby(['measure', 'season']).agg({
    'rate_per_1000': ['mean', 'std'],
    'RR': ['mean', 'std'],
    'rate_diff': ['mean', 'std'],
}).reset_index().round(2)
# Fix column index
sum_win_df.columns = ['_'.join(col).strip('_') for col in sum_win_df.columns.values]
# Merge with the results df
sum_win_df = sum_win_df.merge(results, on=['measure', 'season'], how='left')
sum_win_df['signif_%'] = round((sum_win_df['signif_sum'] / sum_win_df['signif_count']) * 100, 2)
if test:
    sum_win_df.to_csv('output/practice_measures/seasonality_results_test.csv')
else:
    sum_win_df.to_csv('output/practice_measures/seasonality_results.csv')
log_memory_usage(label="After practice-level testing data")

# --------------- Describing long-term trend --------------------------------------------

practice_interval_df['weeks_from_start'] = (
        practice_interval_df['interval_start'] - study_start_date
    ).dt.days / 7
results_dict = {}
for measure in measures:
    # Use mask instead of filter so that view is used instead of copy (saves memory)
    mask = practice_interval_df['measure'] == measure
    # Create column for time since start
    practice_interval_df.loc[mask, 'weeks_from_start'] = (
        practice_interval_df.loc[mask, 'interval_start'] - study_start_date
    ).dt.days / 7
    res_SumBas = stats.linregress(practice_interval_df.loc[mask, 'weeks_from_start'], practice_interval_df.loc[mask, 'RR'])
    res_rate_mp6 = stats.linregress(practice_interval_df.loc[mask, 'weeks_from_start'], practice_interval_df.loc[mask, 'rate_per_1000_midpoint6_derived'])
    results_dict[measure] = {
        "slope_RR": res_SumBas.slope,
        "r_squared_RR": res_SumBas.rvalue**2,
        "variance_RR": stats.variation(practice_interval_df.loc[mask, 'RR']),
        "slope_rate_mp6": res_rate_mp6.slope,
        "r_squared_rate_mp6": res_rate_mp6.rvalue**2,
        "variance_rate_mp6": stats.variation(practice_interval_df.loc[mask, 'rate_per_1000_midpoint6_derived'])
    }

results_df = pd.DataFrame.from_dict(results_dict, orient='index')
# Round results
results_df = results_df.round(4)
if test:
    results_df.to_csv("output/practice_measures/trend_results_test.csv")
else:
    results_df.to_csv("output/practice_measures/trend_results.csv")
log_memory_usage(label="After trend analysis")


