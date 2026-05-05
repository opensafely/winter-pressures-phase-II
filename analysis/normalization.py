# This script normalizes the practice measures data by calculating rate ratios and testing for seasonality.
# It also performs a long-term trend analysis on the rate ratios and rounded rates.
# USAGE: python analysis/normalization.py
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval

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
from itertools import combinations
from scipy.stats import pearsonr, spearmanr
import os

# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(config["study_end_date"], config["n_years"])
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

log_memory_usage(label="Before loading data")

input_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}/proc_{config['group']}_measures"
practice_interval_df = read_write("read", input_path)

print(
    f"1. Total numerator = {practice_interval_df['numerator'].sum()}, \nTotal denominator = {practice_interval_df['list_size'].sum()}, \nTotal practices = {practice_interval_df['practice_pseudo_id'].nunique()}"
)
log_memory_usage(label="After loading data")

# -------- Filter out unrepresentative intervals for calculating RRs ----------------------------------

# Remove interval containing xmas shutdown
date_col = practice_interval_df["interval_start"]
exclude_mask = ((date_col.dt.month == 12) & date_col.dt.day.between(19, 26)) | (
    date_col >= pd.Timestamp("2025-06-01")
)
practice_interval_df = practice_interval_df.loc[~exclude_mask]

practice_interval_df["season"] = practice_interval_df["month"].apply(get_season)

# Only keep intervals inside the periods of interest
practice_interval_df = practice_interval_df.loc[
    practice_interval_df["season"].isin(["Jun-Jul", "Sep-Oct", "Nov-Dec", "Jan-Feb"])
]

# Separate pandemic period from main dataset
pandemic_df = practice_interval_df.loc[
    practice_interval_df["pandemic"].isin(["During"])
]

practice_interval_df = practice_interval_df.loc[
    ~practice_interval_df["pandemic"].isin(["During"])
]
print(
    f"2. Total numerator after filtering = {practice_interval_df['numerator'].sum()}, \nTotal denominator after filtering = {practice_interval_df['list_size'].sum()}, \nTotal practices after filtering = {practice_interval_df['practice_pseudo_id'].nunique()}"
)

# ----------------------- Seasonality analysis ----------------------------------

# Iterate over two summer baseline options: 1) Compare winter to prev summer 2) Compare winter to first summer

non_summer = {}
summer = {}
seasonal_groups = [summer, non_summer]
non_summer["practice_interval_df"] = practice_interval_df[
    practice_interval_df["season"] != "Jun-Jul"
]
summer["practice_interval_df"] = practice_interval_df[
    practice_interval_df["season"] == "Jun-Jul"
]

for seasonal_group in seasonal_groups:

    # -------- VARIANCES --------------------

    ## VARIANCE BETWEEN PRACTICES
    # Calculate variance between practices for each week
    seasonal_group["interval_season_df"] = build_aggregate_df(
        seasonal_group["practice_interval_df"],
        ["measure", "interval_start", "pandemic"],
        {"Rate_per_1000": ["var"]},
    )

    # Identify season for each week
    seasonal_group["interval_season_df"]["season"] = seasonal_group[
        "interval_season_df"
    ]["interval_start"].dt.month.apply(get_season)

    # Aggregate weekly variance btwn practices to median seasonal variance btwn practices
    seasonal_group["season_var_btwn_df"] = build_aggregate_df(
        seasonal_group["interval_season_df"],
        ["measure", "season", "pandemic"],
        {"Rate_per_1000_var": ["median", "count"]},
    )

    # Rename columns for clarity
    seasonal_group["season_var_btwn_df"].rename(
        columns={
            "Rate_per_1000_var_median": "rate_weekly_var_btwn_prac_median",
            "Rate_per_1000_var_count": "rate_weekly_var_btwn_prac_n_weeks",
        },
        inplace=True,
    )

    ## VARIANCE WITHIN PRACTICES
    # Aggregate counts per practice-season, and calculate variance within practices across weeks
    seasonal_group["practice_season_df"] = build_aggregate_df(
        seasonal_group["practice_interval_df"],
        ["measure", "practice_pseudo_id", "season", "pandemic", "summer_year"],
        {"numerator": ["sum"], "Rate_per_1000": ["var"]},
        initial_list_size=True,
    )
    seasonal_group["practice_season_df"][
        "list_size_count"
    ] = 1  # Practice count indicator for later aggregation

    # Aggregate seasonal variance w/in practices to median national seasonal variance w/in practices
    seasonal_group["season_var_w/in_df"] = build_aggregate_df(
        seasonal_group["practice_season_df"],
        ["measure", "season", "pandemic"],
        {"Rate_per_1000_var": ["median", "count"]},
    )

    # Rename columns for clarity
    seasonal_group["season_var_w/in_df"].rename(
        columns={
            "Rate_per_1000_var_median": "rate_weekly_var_w/in_prac_median",
            "Rate_per_1000_var_count": "rate_weekly_var_w/in_prac_n_weeks",
        },
        inplace=True,
    )
    
    print(
        f"3. Total numerator for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['numerator'].sum()}, \nTotal denominator for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['list_size'].sum()}, \nTotal practices for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['practice_pseudo_id'].nunique()}"
    )

# Concatenate summer and non-summer variance tables into one table
combined_var_btwn_df = pd.concat([summer["season_var_btwn_df"], non_summer["season_var_btwn_df"]])
combined_var_within_df = pd.concat([summer["season_var_w/in_df"], non_summer["season_var_w/in_df"]])

# Merge into one variance table
combined_var_btwn_df = combined_var_btwn_df.merge(
    combined_var_within_df,
    on=["measure", "season", "pandemic"],
    how="left",
)

read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Variances",
    df=combined_var_btwn_df,
    file_type="csv",
)


# -------- RATE RATIOS --------------------

## REMOvE PRACTICES WITH ZERO/NAN BASELINE RATES 
keys = ["measure", "summer_year", "practice_pseudo_id"]

# Identify practices with zero/nan baseline rates in summer season to exclude from practice-level RRs 
summer["zero_or_nan_df"] = summer["practice_season_df"][
    (summer["practice_season_df"]["numerator_sum"] == 0)
    | (summer["practice_season_df"]["numerator_sum"].isna())
]

for seasonal_group in seasonal_groups:

    # Merge with zero/nan df to identify practices with zero/nan baseline rates
    seasonal_group["practice_season_df"] = seasonal_group["practice_season_df"].merge(
        summer["zero_or_nan_df"][keys], on=keys, how="left", indicator=True
    )
    print(
        f"7. Total numerator for {seasonal_group['practice_season_df']['season'].iloc[0]} after merging with zero/nan df = {seasonal_group['practice_season_df']['numerator_sum'].sum()}, \nTotal denominator for {seasonal_group['practice_season_df']['season'].iloc[0]} after merging with zero/nan df = {seasonal_group['practice_season_df']['list_size_initial'].sum()}, \nTotal practices for {seasonal_group['practice_season_df']['season'].iloc[0]} after merging with zero/nan df = {seasonal_group['practice_season_df']['practice_pseudo_id'].nunique()}"
    )

    # Keep only practices that do not have zero/nan baseline rates
    seasonal_group["practice_season_df"] = seasonal_group["practice_season_df"][
        seasonal_group["practice_season_df"]["_merge"] == "left_only"
    ].drop(columns="_merge")
    print(
        f"8. Total numerator for {seasonal_group['practice_season_df']['season'].iloc[0]} after removing zero/nan practices = {seasonal_group['practice_season_df']['numerator_sum'].sum()}, \nTotal denominator for {seasonal_group['practice_season_df']['season'].iloc[0]} after removing zero/nan practices = {seasonal_group['practice_season_df']['list_size_initial'].sum()}, \nTotal practices for {seasonal_group['practice_season_df']['season'].iloc[0]} after removing zero/nan practices = {seasonal_group['practice_season_df']['practice_pseudo_id'].nunique()}"
    )

    # -------- PATIENT LEVEL (LIST_SIZE-WEIGHTED) EFFECTS --------------------
    ## Yearly RRs

    seasonal_group["season_df"] = build_aggregate_df(
        seasonal_group["practice_season_df"],
        ["measure", "season", "pandemic", "summer_year"],
        {
            "numerator_sum": ["sum"],
            "list_size_initial": ["sum"],
            "list_size_count": ["sum"],
        },
    )

    print(
        f"9. Total numerator for {seasonal_group['season_df']['season'].iloc[0]} after season-level aggregation = {seasonal_group['season_df']['numerator_sum_sum'].sum()}, \nTotal denominator for {seasonal_group['season_df']['season'].iloc[0]} after season-level aggregation = {seasonal_group['season_df']['list_size_initial_sum'].sum()}, \nTotal practices for {seasonal_group['season_df']['season'].iloc[0]} after season-level aggregation = {seasonal_group['season_df']['list_size_count_sum'].sum()}"
    )

long_df = pd.concat([summer["practice_season_df"], non_summer["practice_season_df"]])

# Remap column names
long_df = long_df.rename(
    columns={
        "numerator_sum": "num_sum",
        "list_size_initial": "list_size_initial",
        "list_size_count": "n_practices",
    }
)
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/practice_level_counts",
    df=long_df,
    file_type="csv",
)

combined_seasons_df = calculate_rate_ratios(
    summer["season_df"], non_summer["season_df"], practice_level=False
)

rename_map = {
    "numerator_sum_sum": "num_sum",
    "list_size_initial_sum": "list_size_initial",
    "list_size_count_sum": "n_practices",
    "numerator_sum_sum_prev_summr": "num_prev_summer",
    "list_size_initial_sum_prev_summr": "list_prev_summer",
    "list_size_count_sum_prev_summr": "n_practices_prev_summer",
    "numerator_sum_sum_first_summr": "num_first_summer",
    "list_size_initial_sum_first_summr": "list_first_summer",
    "list_size_count_sum_first_summr": "n_practices_first_summer",
    "Rate_per_1000": "rate_/1000",
    "Rate_per_1000_prev_summr": "rate_/1000_prev_summer",
    "Rate_per_1000_first_summr": "rate_/1000_first_summer",
    "RR_prev_summr": "RR_prev_summer",
    "RD_prev_summr": "RD_prev_summer",
    "RR_first_summr": "RR_first_summer",
    "RD_first_summr": "RD_first_summer",
}

combined_seasons_df = combined_seasons_df.rename(columns=rename_map)
combined_seasons_df = combined_seasons_df.drop(
    columns=["season_prev_summr", "season_first_summr"]
)
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_weighted",
    df=combined_seasons_df,
    file_type="csv",
)

# Check medians and var ratio
# practice_season_df["var/mean"] = (
#     practice_season_df["Rate_per_1000_var_mean"]
#     / practice_season_df["Rate_per_1000_mean_mean"]
# )

# ------------ PRACTICE-LEVEL (UNWEIGHTED) EFFECT -------------------------

## Practice-level RRs

combined_practice_seasons_df = calculate_rate_ratios(
    summer["practice_season_df"], non_summer["practice_season_df"], practice_level=True
)

# Visualise distributions of rates and RRs
plot_dir = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/plots"
os.makedirs(plot_dir, exist_ok=True)

rate_plots = generate_dist_plot(
    df=combined_practice_seasons_df, var="Rate_per_1000", facet_var="measure"
)
rate_plots.savefig(f"{plot_dir}/rates.png")
RR_plots = generate_dist_plot(
    df=combined_practice_seasons_df, var="RR_prev_summr", facet_var="measure"
)
RR_plots.savefig(f"{plot_dir}/RR_prev_summer.png")
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/practice_level_RR",
    df=combined_practice_seasons_df,
    file_type="arrow",
)

## Yearly RRs
yearly_unweighted_df_results = aggregate_unweighted_rr_results(
    combined_practice_seasons_df,
    ["measure", "season", "pandemic", "summer_year"],
)
rename_map = {
    # rate ratios
    "RR_prev_summr_median": "RR_prev_median",
    "RR_first_summr_median": "RR_first_median",
    # list sizes (counts of practices contributing)
    "list_size_count_first_summr_sum": "n_practice_first_summer",
    "list_size_count_prev_summr_sum": "n_practice_prev_summer",
    # rate differences
    "RD_prev_summr_median": "RD_prev_median",
    "RD_first_summr_median": "RD_first_median",
}

# Save unweighted RRs per year
yearly_unweighted_df_results = yearly_unweighted_df_results.rename(columns=rename_map)
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_unweighted_yearly",
    df=yearly_unweighted_df_results,
    file_type="csv",
)

## Pandemic period RRs
pandemic_unweighted_df_results = aggregate_unweighted_rr_results(
    combined_practice_seasons_df,
    ["measure", "season", "pandemic"],
)

# Save unweighted RRs per pandemic period
pandemic_unweighted_df_results = pandemic_unweighted_df_results.rename(
    columns=rename_map
)
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_unweighted_pandemic",
    df=pandemic_unweighted_df_results,
    file_type="csv",
)

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
#             sub_df["weeks_from_start"], sub_df["rate_per_1000"]
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
#                     sub_df["rate_per_1000"], nan_policy="omit"
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
#     f"output/{args.group}_measures_{args.set}/trend_results",
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
#     f"output/{args.group}_measures_{args.set}/corr_results",
#     df=summary_corr_df,
#     file_type="csv",
# )

# log_memory_usage(label="After trend analysis")

# ------------ PRACTICE LEVEL SIGNIFICANCE TESTING ----------------------

# Apply efficiently (no repeated filtering)
# practice_season_df["test_summer_vs_winter"] = practice_season_df.apply(
#     lambda row: test_difference(row, agg_df), axis=1
# )

# breakpoint()

# values = ['numerator_sum', 'list_size_initial', 'numerator_sum_prev_summr', 'list_size_initial_prev_summr']
# for value in values:
#     combined_practice_seasons_df = combined_practice_seasons_df[combined_practice_seasons_df[value].notna()]
#     if 'list_size' in value:
#         combined_practice_seasons_df = combined_practice_seasons_df[combined_practice_seasons_df[value] > 0]

# def run_poisson_test(row):

#     res = stats.poisson_means_test(
#         row['numerator_sum'], row['list_size_initial'],
#         row['numerator_sum_prev_summr'], row['list_size_initial_prev_summr'],
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
