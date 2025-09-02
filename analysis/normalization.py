# This script normalizes the practice measures data by calculating rate ratios and testing for seasonality.
# It also performs a long-term trend analysis on the rate ratios and rounded rates.
# analysis/normalization.py
# Option --test flag to run a lightweight test using simulated data
# Option --practice OR --demograph OR --comorbid flags to select pipeline
# Option --temp to run a temporary specific section of code and exit early

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
            "rate_per_1000_midpoint6_derived_var_mean": "rate_var_btwn_prac_mean",
            "rate_per_1000_midpoint6_derived_var_count": "rate_var_btwn_prac_n_intervals"
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
        ["measure", "season", "pandemic", "summer_year"],
        {"numerator_midpoint6_sum": ["sum"], "list_size_midpoint6_sum": ["sum"], "list_size_midpoint6_count": ["sum"]},
    )

combined_seasons_df = merge_seasons(summer['season_df'], non_summer['season_df'], practice_level = False)

# Calculate rate ratios
combined_seasons_df[f"rate_per_1000"] = (combined_seasons_df[f'numerator_midpoint6_sum_sum'] / combined_seasons_df[f'list_size_midpoint6_sum_sum'])*1000
baselines = ['_prev_summr', '_first_summr']

for baseline in baselines:
    combined_seasons_df[f"rate_per_1000{baseline}"] = (combined_seasons_df[f'numerator_midpoint6_sum_sum{baseline}'] / combined_seasons_df[f'list_size_midpoint6_sum_sum{baseline}'])*1000
    combined_seasons_df[f"RR{baseline}"] = combined_seasons_df[f"rate_per_1000"] / combined_seasons_df[f"rate_per_1000{baseline}"]
    combined_seasons_df[f"RD{baseline}"] = combined_seasons_df[f"rate_per_1000"] - combined_seasons_df[f"rate_per_1000{baseline}"]

rename_map = {
    "numerator_midpoint6_sum_sum": "num_sum",
    "list_size_midpoint6_sum_sum": "list_sum",
    "list_size_midpoint6_count_sum": "list_count",

    "numerator_midpoint6_sum_sum_prev_summr": "num_prev",
    "list_size_midpoint6_sum_sum_prev_summr": "list_prev",
    "list_size_midpoint6_count_sum_prev_summr": "list_count_prev",

    "numerator_midpoint6_sum_sum_first_summr": "num_first",
    "list_size_midpoint6_sum_sum_first_summr": "list_first",
    "list_size_midpoint6_count_sum_first_summr": "list_count_first",

    "rate_per_1000": "rate",
    "rate_per_1000_prev_summr": "rate_prev",
    "rate_per_1000_first_summr": "rate_first",

    "RR_prev_summr": "RR_prev",
    "RD_prev_summr": "RD_prev",
    "RR_first_summr": "RR_first",
    "RD_first_summr": "RD_first",
}

combined_seasons_df = combined_seasons_df.rename(columns=rename_map)
combined_seasons_df = combined_seasons_df.drop(columns=["season_prev_summr", "season_first_summr"])
read_write(read_or_write="write", path=f"output/{args.group}_measures/Results_weighted", df=combined_seasons_df, file_type = 'csv')    

combined_var_df = summer['season_var_df'].merge(
    non_summer['season_var_df'], on=["measure", "season", "pandemic"], how="left"
)

read_write(read_or_write="write", path=f"output/{args.group}_measures/Results_variance", df=combined_var_df, file_type = 'csv')    

# Check means and var ratio
# practice_season_df["var/mean"] = (
#     practice_season_df["rate_per_1000_midpoint6_derived_var_mean"]
#     / practice_season_df["rate_per_1000_midpoint6_derived_mean_mean"]
# )

# ------------ 4 - PRACTICE-LEVEL (UNWEIGHTED) EFFECT -------------------------

non_summer['practice_season_df']['Rate_per_1000'] = (non_summer['practice_season_df']['numerator_midpoint6_sum'] / non_summer['practice_season_df']['list_size_midpoint6_sum'])*1000
summer['practice_season_df']['Rate_per_1000'] = (summer['practice_season_df']['numerator_midpoint6_sum'] / summer['practice_season_df']['list_size_midpoint6_sum'])*1000

combined_practice_seasons_df = merge_seasons(summer['practice_season_df'], non_summer['practice_season_df'], practice_level = True)

combined_practice_seasons_df['RR_prev_summr'] = combined_practice_seasons_df['Rate_per_1000'] / combined_practice_seasons_df['Rate_per_1000_prev_summr']
combined_practice_seasons_df['RR_first_summr'] = combined_practice_seasons_df['Rate_per_1000'] / combined_practice_seasons_df['Rate_per_1000_first_summr']
combined_practice_seasons_df['RD_prev_summr'] = combined_practice_seasons_df['Rate_per_1000'] - combined_practice_seasons_df['Rate_per_1000_prev_summr']
combined_practice_seasons_df['RD_first_summr'] = combined_practice_seasons_df['Rate_per_1000'] - combined_practice_seasons_df['Rate_per_1000_first_summr']

# Save practice-level counts for downstream stat testing
read_write(read_or_write="write", path=f"output/{args.group}_measures/practice_level_counts", df=combined_practice_seasons_df, file_type = 'arrow')    

# Aggregate from practice level to pandemic level
combined_seasons_df_results = build_aggregate_df(
    combined_practice_seasons_df,
    ["measure", "season", "pandemic"],
    {"RR_prev_summr": ["mean"], "RR_first_summr": ["mean"], "list_size_midpoint6_count_first_summr": ['sum'], "list_size_midpoint6_count_prev_summr": ["sum"],
     "RD_prev_summr": ["mean"], "RD_first_summr": ["mean"]},
)

# Save unweighted RRs per season
rename_map = {
    # rate ratios
    "RR_prev_summr_mean": "RR_prev_mean",
    "RR_first_summr_mean": "RR_first_mean",

    # list sizes (counts of practices contributing)
    "list_size_midpoint6_count_first_summr_sum": "list_count_first",
    "list_size_midpoint6_count_prev_summr_sum": "list_count_prev",

    # rate differences
    "RD_prev_summr_mean": "RD_prev_mean",
    "RD_first_summr_mean": "RD_first_mean",
}
combined_seasons_df_results = combined_seasons_df_results.rename(columns=rename_map)
read_write(read_or_write="write", path=f"output/{args.group}_measures/Results_unweighted", df=combined_seasons_df_results, file_type = 'csv')    

# # --------------- Describing long-term trend --------------------------------------------

# from scipy import stats
# import pandas as pd
# import numpy as np

# results_list = []

# # Loop over each measure
# for measure in measures:
#     # Subset for current measure
#     measure_df = practice_interval_df[practice_interval_df["measure"] == measure].copy()

#     # Get the earliest date for time 0 (can vary per measure)
#     min_date = measure_df["interval_start"].min()

#     # Compute weeks from start
#     measure_df["weeks_from_start"] = (
#         measure_df["interval_start"] - min_date
#     ).dt.days / 7

#     # Loop over each practice
#     for pid, sub_df in measure_df.groupby("practice_pseudo_id"):
#         if len(sub_df) < 2:
#             continue  # skip if insufficient data points

#         # Linear regression: RR vs. time
#         res_rr = stats.linregress(sub_df["weeks_from_start"], sub_df["RR"])
#         # Linear regression: rate vs. time
#         res_rate = stats.linregress(
#             sub_df["weeks_from_start"], sub_df["rate_per_1000_midpoint6_derived"]
#         )

#         # Collect per-practice stats
#         results_list.append(
#             {
#                 "measure": measure,
#                 "practice_pseudo_id": pid,
#                 "slope_RR": res_rr.slope,
#                 "r_squared_RR": res_rr.rvalue**2,
#                 "cv_RR": stats.variation(sub_df["RR"], nan_policy="omit"),
#                 "slope_rate": res_rate.slope,
#                 "r_squared_rate": res_rate.rvalue**2,
#                 "cv_rate": stats.variation(
#                     sub_df["rate_per_1000_midpoint6_derived"], nan_policy="omit"
#                 ),
#             }
#         )

# # Combine into dataframe
# practice_results_df = pd.DataFrame(results_list)

# # Now calculate mean and variance of each stat per measure
# summary_df = practice_results_df.groupby("measure").agg(
#     {
#         "slope_RR": ["mean", "var"],
#         "r_squared_RR": ["mean", "var"],
#         "cv_RR": ["mean", "var"],
#         "slope_rate": ["mean", "var"],
#         "r_squared_rate": ["mean", "var"],
#         "cv_rate": ["mean", "var"],
#     }
# )

# # Flatten column names
# summary_df.columns = ["_".join(col) for col in summary_df.columns]
# summary_df = summary_df.round(4)

# # Save
# read_write(
#     "write",
#     f"output/{args.group}_measures/trend_results",
#     df=summary_df,
#     file_type="csv",
# )

# # Correlation analysis
# correlation_results = []

# # Loop over practices
# for pid, df in practice_interval_df.groupby("practice_pseudo_id"):
#     # Pivot to wide format for this practice
#     pivot_df = df.pivot_table(index="interval_start", columns="measure", values="RR")

#     measure_list = pivot_df.columns.dropna().tolist()
#     measure_pairs = list(combinations(measure_list, 2))

#     for m1, m2 in measure_pairs:
#         pair_df = pivot_df[[m1, m2]].dropna()
#         n = len(pair_df)
#         if n < 2:
#             continue  # need at least 2 points to compute correlation

#         # Compute correlations
#         pearson_r, _ = pearsonr(pair_df[m1], pair_df[m2])
#         spearman_r, _ = spearmanr(pair_df[m1], pair_df[m2])

#         correlation_results.append(
#             {
#                 "practice_pseudo_id": pid,
#                 "measure_1": m1,
#                 "measure_2": m2,
#                 "pearson_r": pearson_r,
#                 "spearman_r": spearman_r,
#                 "n_overlap": n,
#             }
#         )

# # Convert to DataFrame
# correlation_df = pd.DataFrame(correlation_results)

# # Now group by measure pair to get mean and variance across practices
# summary_corr_df = build_aggregate_df(
#     correlation_df,
#     ["measure_1", "measure_2"],
#     {"pearson_r": ["mean", "var"], "spearman_r": ["mean", "var"], "n_overlap": "mean"},
# )
# summary_corr_df = summary_corr_df.rename(
#     columns={"measure_1_": "measure_1", "measure_2_": "measure_2"}
# )

# # Round for readability
# summary_corr_df = summary_corr_df.round(4)

# # Save to file
# read_write(
#     "write",
#     f"output/{args.group}_measures/corr_results",
#     df=summary_corr_df,
#     file_type="csv",
# )

# log_memory_usage(label="After trend analysis")

# ------------ PRACTICE LEVEL SIGNIFICANCE TESTING ----------------------

# Apply efficiently (no repeated filtering)
# practice_season_df["test_summer_vs_winter"] = practice_season_df.apply(
#     lambda row: test_difference(row, agg_df), axis=1
# )

#breakpoint()

# values = ['numerator_midpoint6_sum', 'list_size_midpoint6_sum', 'numerator_midpoint6_sum_prev_summr', 'list_size_midpoint6_sum_prev_summr']
# for value in values:
#     combined_practice_seasons_df = combined_practice_seasons_df[combined_practice_seasons_df[value].notna()]
#     if 'list_size' in value:
#         combined_practice_seasons_df = combined_practice_seasons_df[combined_practice_seasons_df[value] > 0]

# def run_poisson_test(row):
    
#     res = stats.poisson_means_test(
#         row['numerator_midpoint6_sum'], row['list_size_midpoint6_sum'],
#         row['numerator_midpoint6_sum_prev_summr'], row['list_size_midpoint6_sum_prev_summr'],
#         alternative='two-sided'
#     )
    
#     return res.pvalue   # or res.statistic

# combined_practice_seasons_df['test_prev_summr'] = combined_practice_seasons_df.apply(run_poisson_test, axis=1)

# breakpoint()
# # Adjust for multiple testing
# # Identify non-NaN indices
# valid_mask = ~np.isnan(practice_season_df["test_summer_vs_winter"])
# # Run FDR correction only on valid values
# adj_pvals = np.full_like(
#     practice_season_df["test_summer_vs_winter"], np.nan, dtype=float
# )
# adj_pvals[valid_mask] = stats.false_discovery_control(
#     practice_season_df["test_summer_vs_winter"][valid_mask], method="bh"
# )
# practice_season_df["test_summer_vs_winter_adj"] = adj_pvals

# # Calculate proportion of significant results at measure-season level
# practice_season_df["signif"] = practice_season_df["test_summer_vs_winter"] < 0.05
# practice_season_df["signif_adj"] = (
#     practice_season_df["test_summer_vs_winter_adj"] < 0.05
# )

# results = build_aggregate_df(
#     practice_season_df,
#     ["measure", "season", "pandemic"],
#     {
#         "signif": ["sum", "count"],
#         "signif_adj": ["sum"],
#     },
# )

# # Merge with the results df
# results = season_df.merge(
#     results, on=["measure", "season", "pandemic"], how="left"
# )
# results["signif_%"] = (results["signif_sum"] / results["signif_count"]) * 100
# results["signif_%_adj"] = (
#     results["signif_adj_sum"] / results["signif_count"]
# ) * 100


# # Round results
# results = results.round(2)

# log_memory_usage(label="After practice-level testing data")


