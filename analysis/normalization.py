# This script normalizes the practice measures data by calculating rate ratios and testing for seasonality.
# It also performs a long-term trend analysis on the rate ratios and rounded rates.
# analysis/normalization.py
# Option --test flag to run a lightweight test using simulated data
# Option --practice OR --demograph OR --comorbid flags to select pipeline

# TODO:
# 1 

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
practice_interval_df = read_write("read", input_path)

log_memory_usage(label="After loading data")

# -------- Define useful variables ----------------------------------

# Ensure correct datetime format
practice_interval_df["interval_start"] = pd.to_datetime(
    practice_interval_df["interval_start"]
).dt.tz_localize(None)
practice_interval_df["month"] = practice_interval_df["interval_start"].dt.month
# If Jan - May, RR is relative to prev years summer. If June - Dec, RR is relative to same years summer.
practice_interval_df["summer_year"] = np.where(
    practice_interval_df["month"] <= 5,
    practice_interval_df["interval_start"].dt.year - 1,
    practice_interval_df["interval_start"].dt.year,
)

# Calculate rate per 1000
practice_interval_df["rate_per_1000_midpoint6_derived"] = (
    practice_interval_df["numerator_midpoint6"]
    / practice_interval_df["list_size_midpoint6"]
    * 1000
)

# Define pandemic dates
pandemic_conditions = [
    practice_interval_df["interval_start"] < pd.to_datetime(args.pandemic_start),
    (practice_interval_df["interval_start"] >= pd.to_datetime(args.pandemic_start))
    & (practice_interval_df["interval_start"] <= pd.to_datetime(args.pandemic_end)),
    practice_interval_df["interval_start"] > pd.to_datetime(args.pandemic_end),
]
choices = ["Before", "During", "After"]
practice_interval_df["pandemic"] = np.select(pandemic_conditions, choices)

# Remove interval containing xmas shutdown
practice_interval_df = practice_interval_df.loc[
    ~(
        (practice_interval_df["interval_start"].dt.month == 12)
        & (
            (practice_interval_df["interval_start"].dt.day >= 19)
            & (practice_interval_df["interval_start"].dt.day <= 26)
        )
    )
]
practice_interval_df["season"] = practice_interval_df["month"].apply(get_season)

# Only keep intervals inside the periods of interest
practice_interval_df = practice_interval_df.loc[
        practice_interval_df["season"].isin(
            ["Jun-Jul", "Sep-Oct", "Nov-Dec", "Jan-Feb"]
        )
    ]

# ----------------------- Seasonality analysis ----------------------------------

# Iterate over two summer baseline options: 1) Compare winter to prev summer 2) Compare winter to first summer

non_summer ={}
summer = {}
seasonal_groups = [non_summer, summer]
non_summer['practice_interval_df'] = practice_interval_df[practice_interval_df['season'] != 'Jun-Jul']
summer['practice_interval_df'] = practice_interval_df[practice_interval_df['season'] == 'Jun-Jul']

for seasonal_group in seasonal_groups:

    # -------- 1 - VARIANCES --------------------

    seasonal_group['interval_season_df'] = build_aggregate_df(
        seasonal_group['practice_interval_df'],
        ["measure", "interval_start", "pandemic"],
        {"rate_per_1000_midpoint6_derived": ["var"]},
    )
    
    seasonal_group['interval_season_df']['season'] = seasonal_group['interval_season_df'][
        "interval_start"
    ].dt.month.apply(get_season)

    # Variance at each timepoint, averaged per season
    seasonal_group['season_var_df'] = build_aggregate_df(
        seasonal_group['interval_season_df'],
        ["measure", "season", "pandemic"],
        {"rate_per_1000_midpoint6_derived_var": ["mean", "count"]},
    )

    # Rename columns for clarity
    seasonal_group['season_var_df'].rename(
        columns={
            "rate_per_1000_midpoint6_derived_var_mean": "rate_var_btwn_prac_mean_unweighted",
        },
        inplace=True,
    )
    
    # -------- 2 - REMOVE SEASONS WITH MISSING BASELINES --------------------

    # Aggregate counts per practice per season
    seasonal_group['practice_season_df'] = build_aggregate_df(
        seasonal_group['practice_interval_df'],
        ["measure", "practice_pseudo_id", "season", "pandemic", "summer_year"],
        {"numerator_midpoint6": ["sum"], "list_size_midpoint6": ["sum", "count"]},
    )

# Generate total counts per measure per summer
summer['zero_or_nan_df'] = summer['practice_season_df'][
    (summer['practice_season_df']['numerator_midpoint6_sum'] == 0) |
    (summer['practice_season_df']['numerator_midpoint6_sum'].isna())
]
to_remove = summer['zero_or_nan_df'][['measure', 'season', 'summer_year', 'practice_pseudo_id', 'pandemic']]

for seasonal_group in seasonal_groups:

    # Remove seasons without a valid baseline rate
    seasonal_group['practice_season_df'] = pd.concat([seasonal_group['practice_season_df'], to_remove]).drop_duplicates(keep=False)
    
    # -------- 3 - PATIENT LEVEL (LIST_SIZE-WEIGHTED) EFFECTS --------------------

    seasonal_group['season_df'] = build_aggregate_df(
        seasonal_group['practice_season_df'],
        ["measure", "season", "pandemic"],
        {"numerator_midpoint6_sum": ["sum"], "list_size_midpoint6_sum": ["sum"], "list_size_midpoint6_count": ["sum"]},
    )

# Add new column for summer counts to main df
combined_seasons_df = non_summer['practice_season_df'].merge(
    summer['practice_season_df'],
    on=['measure', 'summer_year', 'practice_pseudo_id'],
    how='left',
    suffixes = [None, '_prev_summr']
)
# Find the first valid summer year for each measure
first_summer_years = summer['practice_season_df'].groupby('measure')['summer_year'].min().reset_index()
# Merge to keep only the first summer for a given practice and measure
first_summer_df = (
    summer['practice_season_df'].merge(first_summer_years, on=['measure', 'summer_year'])
    .drop(columns='summer_year')  # Drop original summer_year after filtering
    .rename(columns={'prev_summer_numerator': 'first_summer_numerator',
                        'prev_summer_list_size': 'first_summer_list_size',
                        'prev_summer_n_intervals': 'first_summer_n_intervals'})
)

# Merge first summer counts into main df
combined_seasons_df = combined_seasons_df.merge(
    first_summer_df,
    on= ['measure', 'practice_pseudo_id'],
    how='left',
    suffixes = [None, '_first_summr']
)

# Calculate rate ratios
combined_seasons_df[f"rate_per_1000"] = combined_seasons_df[f'numerator_midpoint6_sum'] / combined_seasons_df[f'list_size_midpoint6_sum']
baselines = ['_prev_summr', '_first_summr']
for baseline in baselines:
    combined_seasons_df[f"rate_per_1000{baseline}"] = combined_seasons_df[f'numerator_midpoint6_sum{baseline}'] / combined_seasons_df[f'list_size_midpoint6_sum{baseline}']
    combined_seasons_df[f"RR{baseline}"] = combined_seasons_df[f"rate_per_1000"] / combined_seasons_df[f"rate_per_1000{baseline}"]
    combined_seasons_df[f"RD{baseline}"] = combined_seasons_df[f"rate_per_1000"] - combined_seasons_df[f"rate_per_1000{baseline}"]

read_write(read_or_write="write", path=f"output/{args.group}_measures/Seasonal_counts", df=combined_seasons_df, file_type = 'csv')    

# Check means and var ratio
# practice_season_df["var/mean"] = (
#     practice_season_df["rate_per_1000_midpoint6_derived_var_mean"]
#     / practice_season_df["rate_per_1000_midpoint6_derived_mean_mean"]
# )

# Rename columns for clarity
practice_season_df.rename(
    columns={
        "rate_per_1000_midpoint6_derived_mean_mean": "rate_mean_per_prac_ave",
        "rate_per_1000_midpoint6_derived_mean_count": "rate_N_practices",
        "rate_per_1000_midpoint6_derived_var_mean": "rate_var_per_prac_ave",
        "RR_mean_mean": "RR_mean_per_prac_ave",
        "rate_per_1000_midpoint6_derived_mean_count": "RR_N_practices",
        "RD_var_mean": "RD_var_per_prac_ave",
    },
    inplace=True,
)
# Merge with practice_season_df
season_df = season_df.merge(
    practice_season_df, on=["measure", "season", "pandemic"], how="left"
)

# Apply efficiently (no repeated filtering)
practice_season_df["test_summer_vs_winter"] = practice_season_df.apply(
    lambda row: test_difference(row, agg_df), axis=1
)

# -------- 3 - PRACTICE LEVEL (UNWEIGHTED) EFFECTS -------------------- 

# Adjust for multiple testing
# Identify non-NaN indices
valid_mask = ~np.isnan(practice_season_df["test_summer_vs_winter"])
# Run FDR correction only on valid values
adj_pvals = np.full_like(
    practice_season_df["test_summer_vs_winter"], np.nan, dtype=float
)
adj_pvals[valid_mask] = stats.false_discovery_control(
    practice_season_df["test_summer_vs_winter"][valid_mask], method="bh"
)
practice_season_df["test_summer_vs_winter_adj"] = adj_pvals

# Calculate proportion of significant results at measure-season level
practice_season_df["signif"] = practice_season_df["test_summer_vs_winter"] < 0.05
practice_season_df["signif_adj"] = (
    practice_season_df["test_summer_vs_winter_adj"] < 0.05
)

results = build_aggregate_df(
    practice_season_df,
    ["measure", "season", "pandemic"],
    {
        "signif": ["sum", "count"],
        "signif_adj": ["sum"],
    },
)

# Merge with the results df
results = season_df.merge(
    results, on=["measure", "season", "pandemic"], how="left"
)
results["signif_%"] = (results["signif_sum"] / results["signif_count"]) * 100
results["signif_%_adj"] = (
    results["signif_adj_sum"] / results["signif_count"]
) * 100


# Round results
results = results.round(2)

# Save results
read_write(
    "write",
    f"output/{args.group}_measures/seasonality_results_{baseline}",
    df=results,
    file_type="csv",
)
log_memory_usage(label="After practice-level testing data")

# --------------- Describing long-term trend --------------------------------------------

from scipy import stats
import pandas as pd
import numpy as np

results_list = []

# Loop over each measure
for measure in measures:
    # Subset for current measure
    measure_df = practice_interval_df[practice_interval_df["measure"] == measure].copy()

    # Get the earliest date for time 0 (can vary per measure)
    min_date = measure_df["interval_start"].min()

    # Compute weeks from start
    measure_df["weeks_from_start"] = (
        measure_df["interval_start"] - min_date
    ).dt.days / 7

    # Loop over each practice
    for pid, sub_df in measure_df.groupby("practice_pseudo_id"):
        if len(sub_df) < 2:
            continue  # skip if insufficient data points

        # Linear regression: RR vs. time
        res_rr = stats.linregress(sub_df["weeks_from_start"], sub_df["RR"])
        # Linear regression: rate vs. time
        res_rate = stats.linregress(
            sub_df["weeks_from_start"], sub_df["rate_per_1000_midpoint6_derived"]
        )

        # Collect per-practice stats
        results_list.append(
            {
                "measure": measure,
                "practice_pseudo_id": pid,
                "slope_RR": res_rr.slope,
                "r_squared_RR": res_rr.rvalue**2,
                "cv_RR": stats.variation(sub_df["RR"], nan_policy="omit"),
                "slope_rate": res_rate.slope,
                "r_squared_rate": res_rate.rvalue**2,
                "cv_rate": stats.variation(
                    sub_df["rate_per_1000_midpoint6_derived"], nan_policy="omit"
                ),
            }
        )

# Combine into dataframe
practice_results_df = pd.DataFrame(results_list)

# Now calculate mean and variance of each stat per measure
summary_df = practice_results_df.groupby("measure").agg(
    {
        "slope_RR": ["mean", "var"],
        "r_squared_RR": ["mean", "var"],
        "cv_RR": ["mean", "var"],
        "slope_rate": ["mean", "var"],
        "r_squared_rate": ["mean", "var"],
        "cv_rate": ["mean", "var"],
    }
)

# Flatten column names
summary_df.columns = ["_".join(col) for col in summary_df.columns]
summary_df = summary_df.round(4)

# Save
read_write(
    "write",
    f"output/{args.group}_measures/trend_results",
    df=summary_df,
    file_type="csv",
)

# Correlation analysis
correlation_results = []

# Loop over practices
for pid, df in practice_interval_df.groupby("practice_pseudo_id"):
    # Pivot to wide format for this practice
    pivot_df = df.pivot_table(index="interval_start", columns="measure", values="RR")

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

        correlation_results.append(
            {
                "practice_pseudo_id": pid,
                "measure_1": m1,
                "measure_2": m2,
                "pearson_r": pearson_r,
                "spearman_r": spearman_r,
                "n_overlap": n,
            }
        )

# Convert to DataFrame
correlation_df = pd.DataFrame(correlation_results)

# Now group by measure pair to get mean and variance across practices
summary_corr_df = build_aggregate_df(
    correlation_df,
    ["measure_1", "measure_2"],
    {"pearson_r": ["mean", "var"], "spearman_r": ["mean", "var"], "n_overlap": "mean"},
)
summary_corr_df = summary_corr_df.rename(
    columns={"measure_1_": "measure_1", "measure_2_": "measure_2"}
)

# Round for readability
summary_corr_df = summary_corr_df.round(4)

# Save to file
read_write(
    "write",
    f"output/{args.group}_measures/corr_results",
    df=summary_corr_df,
    file_type="csv",
)

log_memory_usage(label="After trend analysis")
