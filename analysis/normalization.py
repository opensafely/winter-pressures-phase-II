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
from itertools import combinations
from scipy.stats import pearsonr, spearmanr

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
# If Jan - May, RR is relative to prev years summer. If June - Dec, RR is relative to same years summer.
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
summer_df = practice_interval_df[practice_interval_df['season'] == 'Jun-Jul']
prev_summer_df = (
    summer_df.groupby(['measure', 'summer_year', 'practice_pseudo_id'])['rate_per_1000_midpoint6_derived']
    .agg(['mean'])
    .rename(columns={'mean': 'prev_summer_mean'})
    .reset_index()
)

# Add new column for summer mean to the main df
practice_interval_df = practice_interval_df.merge(
    prev_summer_df,
    on=['measure', 'summer_year', 'practice_pseudo_id'],
    how='left'
)
# Remove rows for years where the summer baseline rate is 0 and not null
practice_interval_df = practice_interval_df[(practice_interval_df['prev_summer_mean'] > 0) & 
                     ~(practice_interval_df['prev_summer_mean'].isnull())]
prev_summer_df = prev_summer_df[(prev_summer_df['prev_summer_mean'] > 0) & 
                     ~(prev_summer_df['prev_summer_mean'].isnull())]

# Find the first summer year per measure
first_summer_years = prev_summer_df.groupby('measure')['summer_year'].min().reset_index()
# Merge to keep only rows where summer_year equals the first summer for that measure
first_summer_df = (
    prev_summer_df.merge(first_summer_years, on=['measure', 'summer_year'])
    .drop(columns='summer_year')  # Drop original summer_year after filtering
    .rename(columns={'prev_summer_mean': 'first_summer_mean'})
)

# Merge using only 'measure', so every row gets the same baseline per measure
practice_interval_df = practice_interval_df.merge(
    first_summer_df,
    on= ['measure', 'practice_pseudo_id'],
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

    practice_interval_sum_win_df = practice_interval_df.loc[practice_interval_df['season'].isin(['Jun-Jul', 'Sep-Oct', 'Nov-Dec', 'Jan-Feb'])]

    # Test for seasonality at practice-measure-season-level
    # Create practice-measure-season df
    practices = practice_interval_sum_win_df['practice_pseudo_id'].unique()
    measures = practice_interval_sum_win_df['measure'].unique()
    seasons = practice_interval_sum_win_df['season'].unique()
    pandemics = practice_interval_sum_win_df['pandemic'].unique()
    permutations = list(product(practices, measures, seasons, pandemics))
    practice_sum_win_df = pd.DataFrame(permutations, columns=['practice_pseudo_id', 'measure', 'season', 'pandemic'])

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

    # Mean and variance at each timepoint
    interval_sum_win_df = practice_interval_sum_win_df.groupby(['measure', 'interval_start', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived': ['mean', 'var'],
        'RR': ['mean', 'var'],
        'RD': ['mean', 'var'],
    }).reset_index()
    interval_sum_win_df.columns = ['_'.join(col).strip('_') for col in interval_sum_win_df.columns.values]
    interval_sum_win_df['season'] = interval_sum_win_df['interval_start'].dt.month.apply(get_season)
    # Mean and variance at each timepoint, averaged per season
    sum_win_df = interval_sum_win_df.groupby(['measure', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived_mean': ['mean', 'count'],
        'rate_per_1000_midpoint6_derived_var': ['mean'],
        'RR_mean': ['mean', 'count'],
        'RD_var': ['mean'],
    }).reset_index()
    sum_win_df.columns = ['_'.join(col).strip('_') for col in sum_win_df.columns.values]
    # Rename columns for clarity
    sum_win_df.rename(columns={
        'rate_per_1000_midpoint6_derived_mean_mean': 'rate_mean_over_t_ave',
        'rate_per_1000_midpoint6_derived_mean_count': 'rate_N_timepoints',
        'rate_per_1000_midpoint6_derived_var_mean': 'rate_var_over_t_ave',
        'RR_mean_mean': 'RR_mean_over_t_ave',
        'RR_mean_count': 'RR_N_timepoints',
        'RD_var_mean': 'RD_var_over_t_ave'
    }, inplace=True)

    # Mean and variance per practice
    practice_sum_win_df = practice_interval_sum_win_df.groupby(['measure', 'practice_pseudo_id', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived': ['mean', 'var'],
        'RR': ['mean', 'var'],
        'RD': ['mean', 'var'],
    }).reset_index()
    practice_sum_win_df.columns = ['_'.join(col).strip('_') for col in practice_sum_win_df.columns.values]
    # Mean and variance per practice, averaged per season
    practice_sum_win_df = practice_sum_win_df.groupby(['measure', 'season', 'pandemic']).agg({
        'rate_per_1000_midpoint6_derived_mean': ['mean', 'count'],
        'rate_per_1000_midpoint6_derived_var': ['mean'],
        'RR_mean': ['mean', 'count'],
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
        'rate_per_1000_midpoint6_derived_mean_mean': 'rate_mean_per_prac_ave',
        'rate_per_1000_midpoint6_derived_mean_count': 'rate_N_practices',
        'rate_per_1000_midpoint6_derived_var_mean': 'rate_var_per_prac_ave',
        'RR_mean_mean': 'RR_mean_per_prac_ave',
        'rate_per_1000_midpoint6_derived_mean_count': 'RR_N_practices',
        'RD_var_mean': 'RD_var_per_prac_ave'
    }, inplace=True)
    # Merge with practice_sum_win_df
    sum_win_df = sum_win_df.merge(practice_sum_win_df, on=['measure', 'season', 'pandemic'], how='left')

    # Merge with the results df
    results = sum_win_df.merge(results, on=['measure', 'season', 'pandemic'], how='left')
    results['signif_%'] = (results['signif_sum'] / results['signif_count']) * 100
    results['signif_%_adj'] = (results['signif_adj_sum'] / results['signif_count']) * 100

    # Round results
    results = results.round(2)

    # Save results
    read_write('write', f'output/{args.group}_measures/seasonality_results_{baseline}', df = results, file_type = 'csv')
    log_memory_usage(label="After practice-level testing data")

# --------------- Describing long-term trend --------------------------------------------

from scipy import stats
import pandas as pd
import numpy as np

results_list = []

# Loop over each measure
for measure in measures:
    # Subset for current measure
    measure_df = practice_interval_df[practice_interval_df['measure'] == measure].copy()

    # Get the earliest date for time 0 (can vary per measure)
    min_date = measure_df['interval_start'].min()

    # Compute weeks from start
    measure_df['weeks_from_start'] = (measure_df['interval_start'] - min_date).dt.days / 7

    # Loop over each practice
    for pid, sub_df in measure_df.groupby('practice_pseudo_id'):
        if len(sub_df) < 2:
            continue  # skip if insufficient data points

        # Linear regression: RR vs. time
        res_rr = stats.linregress(sub_df['weeks_from_start'], sub_df['RR'])
        # Linear regression: rate vs. time
        res_rate = stats.linregress(sub_df['weeks_from_start'], sub_df['rate_per_1000_midpoint6_derived'])

        # Collect per-practice stats
        results_list.append({
            'measure': measure,
            'practice_pseudo_id': pid,
            'slope_RR': res_rr.slope,
            'r_squared_RR': res_rr.rvalue**2,
            'cv_RR': stats.variation(sub_df['RR'], nan_policy='omit'),

            'slope_rate': res_rate.slope,
            'r_squared_rate': res_rate.rvalue**2,
            'cv_rate': stats.variation(sub_df['rate_per_1000_midpoint6_derived'], nan_policy='omit')
        })

# Combine into dataframe
practice_results_df = pd.DataFrame(results_list)

# Now calculate mean and variance of each stat per measure
summary_df = practice_results_df.groupby('measure').agg({
    'slope_RR': ['mean', 'var'],
    'r_squared_RR': ['mean', 'var'],
    'cv_RR': ['mean', 'var'],
    'slope_rate': ['mean', 'var'],
    'r_squared_rate': ['mean', 'var'],
    'cv_rate': ['mean', 'var']
})

# Flatten column names
summary_df.columns = ['_'.join(col) for col in summary_df.columns]
summary_df = summary_df.round(4)

# Save
read_write('write', f'output/{args.group}_measures/trend_results', df=summary_df, file_type='csv')

# Correlation analysis
correlation_results = []

# Loop over practices
for pid, df in practice_interval_df.groupby("practice_pseudo_id"):
    # Pivot to wide format for this practice
    pivot_df = df.pivot_table(
        index="interval_start",
        columns="measure",
        values="RR"
    )

    measure_list = pivot_df.columns.dropna().tolist()
    measure_pairs = list(combinations(measure_list, 2))

    for m1, m2 in measure_pairs:
        pair_df = pivot_df[[m1, m2]].dropna()
        n = len(pair_df)
        if n < 2:
            continue  # need at least 2 points to compute correlation

        # Compute correlations
        pearson_r, _ = pearsonr(pair_df[m1], pair_df[m2])
        spearman_r, _ = spearmanr(pair_df[m1], pair_df[m2])

        correlation_results.append({
            'practice_pseudo_id': pid,
            'measure_1': m1,
            'measure_2': m2,
            'pearson_r': pearson_r,
            'spearman_r': spearman_r,
            'n_overlap': n
        })

# Convert to DataFrame
correlation_df = pd.DataFrame(correlation_results)

# Now group by measure pair to get mean and variance across practices
summary_corr_df = correlation_df.groupby(['measure_1', 'measure_2']).agg({
    'pearson_r': ['mean', 'var'],
    'spearman_r': ['mean', 'var'],
    'n_overlap': 'mean'
}).reset_index()

# Flatten columns
summary_corr_df.columns = ['_'.join(col).strip('_') for col in summary_corr_df.columns.values]
summary_corr_df = summary_corr_df.rename(columns={
    'measure_1_': 'measure_1',
    'measure_2_': 'measure_2'
})

# Round for readability
summary_corr_df = summary_corr_df.round(4)

# Save to file
read_write('write', f'output/{args.group}_measures/corr_results', df=summary_corr_df, file_type='csv')

log_memory_usage(label="After trend analysis")


