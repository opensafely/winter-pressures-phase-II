# This script normalizes the practice measures data by calculating rate ratios and testing for seasonality.
# It also performs a long-term trend analysis on the rate ratios and rounded rates.
# Option --test flag to run a lightweight test using simulated data

#TODO:
# 1. Check assumptions for poissoin

import pandas as pd
from utils import *
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np
import random 
from datetime import datetime, timedelta
from scipy import stats
from itertools import product
import pyarrow.feather as feather

# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(args.study_end_date, args.n_years)
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

log_memory_usage(label="Before loading data")
input_path = f"output/{args.group}_measures/proc_{args.group}_measures_midpoint6"
practice_interval_df = read_write('read', input_path)

log_memory_usage(label="After loading data")

# -------- Define useful variables ----------------------------------

# Ensure correct datetime format
practice_interval_df['interval_start'] = pd.to_datetime(practice_interval_df['interval_start']).dt.tz_localize(None)
practice_interval_df['month'] = practice_interval_df['interval_start'].dt.month
practice_interval_df['summer_year'] = np.where( practice_interval_df['month'] <= 5, 
                                                practice_interval_df['interval_start'].dt.year - 1,
                                                practice_interval_df['interval_start'].dt.year)

# Calculate rate per 1000
practice_interval_df['rate_per_1000_midpoint6_derived'] = practice_interval_df['numerator_midpoint6'] / practice_interval_df['list_size_midpoint6'] * 1000

# Define pandemic dates
pandemic_conditions = [
    practice_interval_df['interval_start'] < pd.to_datetime(args.pandemic_start),
        (practice_interval_df['interval_start'] >= pd.to_datetime(args.pandemic_start)) & 
        (practice_interval_df['interval_start'] <= pd.to_datetime(args.pandemic_end)),
    practice_interval_df['interval_start'] > pd.to_datetime(args.pandemic_end)
]
choices = ['Before', 'During', 'After'] 
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

# Create smaller df, summarized at season level using mean
# This is used as a reference for the rate ratio calculation
prev_summer_df = practice_interval_df[practice_interval_df['season'] == 'Jun-Jul']
prev_summer_df = (
    prev_summer_df.groupby(['measure', 'summer_year'])['rate_per_1000_midpoint6_derived']
    .agg(['mean'])
    .rename(columns={'mean': 'prev_summer_mean'})
    .reset_index()
)
# Add new column for summer mean to the main df
practice_interval_df = practice_interval_df.merge(
    prev_summer_df,
    on=['measure', 'summer_year'],
    how='left'
)

# Create summer df version with only first summer
first_summer_df = (
    prev_summer_df[prev_summer_df['summer_year'] == prev_summer_df['summer_year'].min()]
    .drop(columns='summer_year')  # Remove since it's not needed in merge
    .rename(columns={'prev_summer_mean': 'first_summer_mean'})
)
# Merge using only 'measure', so every row gets the same baseline per measure
practice_interval_df = practice_interval_df.merge(
    first_summer_df,
    on='measure',
    how='left'
)

# ----------------------- Seasonality analysis ----------------------------------

# Iterate over two summer baseline options: 1) Compare winter to prev summer 2) Compare winter to first summer
baselines = ['first_summer_mean', 'prev_summer_mean']
for baseline in baselines:

    # Calculate relative rates at for all intervals
    practice_interval_df['RR'] = practice_interval_df['rate_per_1000_midpoint6_derived'] / practice_interval_df[baseline]
    practice_interval_df['RD'] = practice_interval_df['rate_per_1000_midpoint6_derived'] - practice_interval_df[baseline]

    # Save full dataset of rate ratios (essentially de-trended rates)
    output_path = f"output/{args.group}_measures/RR_{baseline}"
    read_write(read_or_write = 'write', path = output_path, df = practice_interval_df)

    # Remove intervals where the rate is 0
    practice_interval_df = practice_interval_df.loc[practice_interval_df['rate_per_1000_midpoint6_derived'] > 0]
    # Filter for summer and winter
    practice_interval_sum_win_df = practice_interval_df.loc[practice_interval_df['season'].isin(['Jun-Jul', 'Sep-Oct', 'Nov-Dec', 'Jan-Feb'])]

    # Test for seasonality at practice-measure-season-level
    # Create practice-measure-season df
    practices = practice_interval_sum_win_df['practice_pseudo_id'].unique()
    measures = practice_interval_sum_win_df['measure'].unique()
    seasons = practice_interval_sum_win_df['season'].unique()
    pandemics = practice_interval_sum_win_df['pandemic'].unique()
    combinations = list(product(practices, measures, seasons, pandemics))
    practice_sum_win_df = pd.DataFrame(combinations, columns=['practice_pseudo_id', 'measure', 'season', 'pandemic'])

    # Apply poisson means test to each practice-measure-season combination
    # Precompute aggregates
    agg_df = build_aggregates(practice_interval_sum_win_df)
    # Apply efficiently (no repeated filtering)
    practice_sum_win_df['test_summer_vs_winter'] = practice_sum_win_df.apply(lambda row: test_difference(row, agg_df), axis=1)
    # Adjust for multiple testing
    # Identify non-NaN indices
    valid_mask = ~np.isnan(practice_sum_win_df['test_summer_vs_winter'])
    # Run FDR correction only on valid values
    adj_pvals = np.full_like(practice_sum_win_df['test_summer_vs_winter'], np.nan, dtype=float)
    adj_pvals[valid_mask] = stats.false_discovery_control(
        practice_sum_win_df['test_summer_vs_winter'][valid_mask], 
        method="bh")
    practice_sum_win_df['test_summer_vs_winter_adj'] = adj_pvals

    # Calculate proportion of significant results at measure-season level
    practice_sum_win_df['signif'] = practice_sum_win_df['test_summer_vs_winter'] < 0.05
    practice_sum_win_df['signif_adj'] = practice_sum_win_df['test_summer_vs_winter_adj'] < 0.05

    results = practice_sum_win_df.groupby(['measure', 'season', 'pandemic']).agg({
        'signif': ['sum', 'count'],
        'signif_adj': ['sum'],
    }).reset_index()
    # Fix column index
    results.columns = ['_'.join(col).strip('_') for col in results.columns.values]

    # Within practice variance
    interval_sum_win_df = practice_interval_sum_win_df.groupby(['measure', 'interval_start', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived': ['mean', 'var'],
        'RR': ['mean', 'var'],
        'RD': ['mean', 'var'],
    }).reset_index()
    interval_sum_win_df.columns = ['_'.join(col).strip('_') for col in interval_sum_win_df.columns.values]
    interval_sum_win_df['season'] = interval_sum_win_df['interval_start'].dt.month.apply(get_season)
    sum_win_df = interval_sum_win_df.groupby(['measure', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived_mean': ['mean'],
        'rate_per_1000_midpoint6_derived_var': ['mean'],
        'RR_mean': ['mean'],
        'RD_var': ['mean'],
    }).reset_index()
    sum_win_df.columns = ['_'.join(col).strip('_') for col in sum_win_df.columns.values]
    # Rename columns for clarity
    sum_win_df.rename(columns={
        'rate_per_1000_midpoint6_derived_mean_mean': 'rate_mean_w/in_prac_mean',
        'rate_per_1000_midpoint6_derived_var_mean': 'rate_var_w/in_prac_mean',
        'RR_mean_mean': 'RR_mean_w/in_prac_mean',
        'RD_var_mean': 'RD_var_w/in_prac_mean'
    }, inplace=True)

    # Between practice variance
    practice_sum_win_df = practice_interval_sum_win_df.groupby(['measure', 'practice_pseudo_id', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived': ['mean', 'var'],
        'RR': ['mean', 'var'],
        'RD': ['mean', 'var'],
    }).reset_index()
    practice_sum_win_df.columns = ['_'.join(col).strip('_') for col in practice_sum_win_df.columns.values]
    practice_sum_win_df = practice_sum_win_df.groupby(['measure', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived_mean': ['mean'],
        'rate_per_1000_midpoint6_derived_var': ['mean'],
        'RR_mean': ['mean'],
        'RD_var': ['mean'],
    }).reset_index()
    practice_sum_win_df.columns = ['_'.join(col).strip('_') for col in practice_sum_win_df.columns.values]
    # Check means and var ratio
    practice_sum_win_df["var/mean"] = (
        practice_sum_win_df["rate_per_1000_midpoint6_derived_var_mean"] /
        practice_sum_win_df["rate_per_1000_midpoint6_derived_mean_mean"]
    )
    # Rename columns for clarity
    practice_sum_win_df.rename(columns={
        'rate_per_1000_midpoint6_derived_mean_mean': 'rate_mean_bw_prac_mean',
        'rate_per_1000_midpoint6_derived_var_mean': 'rate_var_bw_prac_mean',
        'RR_mean_mean': 'RR_mean_bw_prac_mean',
        'RD_var_mean': 'RD_var_bw_prac_mean'
    }, inplace=True)
    # Merge with practice_sum_win_df
    sum_win_df = sum_win_df.merge(practice_sum_win_df, on=['measure', 'season', 'pandemic'], how='left')

    # Merge with the results df
    results = sum_win_df.merge(results, on=['measure', 'season', 'pandemic'], how='left')
    results['signif_%'] = (results['signif_sum'] / results['signif_count']) * 100
    results['signif_%_adj'] = (results['signif_adj_sum'] / results['signif_count']) * 100

    # Round results
    results = results.round(2)
    # Check calculations
    print(f"Matches between means, expect all to match: {(results['rate_mean_bw_prac_mean'] == results['rate_mean_w/in_prac_mean']).sum()}/{len(results)}")
    print(f"Matches between vars, expect none to match: {(results['rate_var_bw_prac_mean'] == results['rate_var_w/in_prac_mean']).sum()}/{len(results)}")
    # Save results
    if args.test:
        results.to_csv(f'output/{args.group}_measures/seasonality_results_{baseline}_test.csv')
    else:
        results.to_csv(f'output/{args.group}_measures/seasonality_results_{baseline}.csv')
    log_memory_usage(label="After practice-level testing data")

# --------------- Describing long-term trend --------------------------------------------

# Uses 'prev_summer_baseline' as that was the last iteration of the baseline loop
practice_interval_df['weeks_from_start'] = (
        practice_interval_df['interval_start'] - args.study_start_date
    ).dt.days / 7
results_dict = {}
for measure in measures:
    # Use mask instead of filter so that view is used instead of copy (saves memory)
    mask = practice_interval_df['measure'] == measure
    # Create column for time since start
    practice_interval_df.loc[mask, 'weeks_from_start'] = (
        practice_interval_df.loc[mask, 'interval_start'] - args.study_start_date
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
if args.test:
    results_df.to_csv("output/practice_measures/trend_results_test.csv")
else:
    results_df.to_csv("output/practice_measures/trend_results.csv")
log_memory_usage(label="After trend analysis")


