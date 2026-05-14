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
from scipy import stats, test
from itertools import product
import pyarrow.feather as feather
from itertools import combinations
from scipy.stats import pearsonr, spearmanr
import os

# ------- CONFIGURATION ----------------------------------

if not config["test"]:
    MEASURES_END_DATE = "2025-06-01"  # Exclude intervals after June 2025 as the set of comparisons are not yet complete
else:
    MEASURES_END_DATE = "2026-06-01"  # For test data, push back end of measures to allow for simulated data

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
    date_col >= pd.Timestamp(MEASURES_END_DATE)
)
practice_interval_df = practice_interval_df.loc[~exclude_mask]
practice_interval_df["season"] = practice_interval_df["month"].apply(get_season)

# Only keep intervals inside the periods of interest
practice_interval_df = practice_interval_df.loc[
    ~(practice_interval_df["season"] == None)
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

#
practice_interval_denominator_df = practice_interval_df.sort_values(
    ["practice_pseudo_id", "interval_start", "measure"]
).drop_duplicates(subset=["practice_pseudo_id", "interval_start"], keep="first")[
    [
        "practice_pseudo_id",
        "interval_start",
        "season",
        "pandemic",
        "summer_year",
        "list_size",
    ]
]

# Exctract list of measures
measure_names_df = practice_interval_df[["measure"]].drop_duplicates()

# ----------------------- Seasonality analysis ----------------------------------

# Iterate over two summer baseline options: 1) Compare winter to prev summer 2) Compare winter to first summer

non_summer = {}
summer = {}
seasonal_groups = [summer, non_summer]

# Add indicator column for seasonal dataframes
summer["is_summer"] = True
non_summer["is_summer"] = False

# Filter numerator counts for specific season
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
        {"Rate_per_1000_var": ["median", "mean", "count"]},
    )

    # Rename columns for clarity
    seasonal_group["season_var_btwn_df"].rename(
        columns={
            "Rate_per_1000_var_median": "var_rate_btwn_prac_season_median",
            "Rate_per_1000_var_mean": "var_rate_btwn_prac_season_mean",
            "Rate_per_1000_var_count": "var_rate_btwn_prac_season_n_weeks",
        },
        inplace=True,
    )

    ## VARIANCE WITHIN PRACTICES
    # Aggregate counts per practice-season, and calculate variance within practices across weeks
    seasonal_group["practice_season_numerator_df"] = build_aggregate_df(
        seasonal_group["practice_interval_df"],
        ["measure", "practice_pseudo_id", "season", "pandemic", "summer_year"],
        {"numerator": ["sum"], "Rate_per_1000": ["var"]},
    )

    # Filter denominator table to season
    if seasonal_group["is_summer"]:
        seasonal_denominator_interval_df = practice_interval_denominator_df[
            practice_interval_denominator_df["season"] == "Jun-Jul"
        ]
    else:
        seasonal_denominator_interval_df = practice_interval_denominator_df[
            practice_interval_denominator_df["season"] != "Jun-Jul"
        ]

    # Merge with all measures to create a practice-season-measure level frame, with consistent denominator counts across measures but allowing denominator counts to vary by season and pandemic period
    seasonal_denominator_df = (
        # Sort denomainator table so that intervals are in order
        seasonal_denominator_interval_df.sort_values(
            [
                "practice_pseudo_id",
                "season",
                "pandemic",
                "summer_year",
                "interval_start",
            ]
        )
        # Pick the first week for each practice-season combination to represent the denominator for that practice-season
        .drop_duplicates(
            subset=["practice_pseudo_id", "season", "pandemic", "summer_year"],
            keep="first",
        ).rename(columns={"list_size": "list_size_initial"})
    )

    # Drop interval_start as the week represents the denominator for the whole season
    seasonal_denominator_df = seasonal_denominator_df.drop(columns=["interval_start"])

    # Add count column to later aggregate number of practices contributing to each season
    seasonal_denominator_df["list_size_count"] = 1

    # Add each permutation of measure with seasonal denominator
    seasonal_denominator_df = seasonal_denominator_df.merge(
        measure_names_df, how="cross"
    )

    # Add the numerator counts for each measure and season
    seasonal_group["practice_season_df"] = seasonal_denominator_df.merge(
        seasonal_group["practice_season_numerator_df"],
        on=["measure", "practice_pseudo_id", "season", "pandemic", "summer_year"],
        how="left",
    )
    seasonal_group["practice_season_df"]["numerator_sum"] = seasonal_group[
        "practice_season_df"
    ]["numerator_sum"].fillna(0)

    # Aggregate seasonal variance w/in practices to median national seasonal variance w/in practices
    seasonal_group["season_var_w/in_df"] = build_aggregate_df(
        seasonal_group["practice_season_df"],
        ["measure", "season", "pandemic"],
        {"Rate_per_1000_var": ["median", "mean", "count"]},
    )

    # Rename columns for clarity
    seasonal_group["season_var_w/in_df"].rename(
        columns={
            "Rate_per_1000_var_median": "var_rate_w/in_prac_season_median",
            "Rate_per_1000_var_mean": "var_rate_w/in_prac_season_mean",
            "Rate_per_1000_var_count": "var_rate_w/in_prac_season_n_practice-years",
        },
        inplace=True,
    )

    print(
        f"3. Total numerator for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['numerator'].sum()}, \nTotal denominator for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['list_size'].sum()}, \nTotal practices for {seasonal_group['practice_interval_df']['season'].iloc[0]} = {seasonal_group['practice_interval_df']['practice_pseudo_id'].nunique()}"
    )

# Concatenate summer and non-summer variance tables into one table
combined_var_btwn_df = pd.concat(
    [summer["season_var_btwn_df"], non_summer["season_var_btwn_df"]]
)
combined_var_within_df = pd.concat(
    [summer["season_var_w/in_df"], non_summer["season_var_w/in_df"]]
)

# Apply SDC rounding
# (Not applied to variance because N is high enough such that variance is undisclosive (ref SACRO guidebook 2023))
# (and rounding the input practice-week rates would distort variance significantly)
combined_var_btwn_df = roundmid_any(
    combined_var_btwn_df, ["var_rate_btwn_prac_season_n_weeks"], to=6
)
combined_var_within_df = roundmid_any(
    combined_var_within_df, ["var_rate_w/in_prac_season_n_practice-years"], to=6
)

# Round tables to 4 dp, except for variances, which are rounded to 6 dp to preserve precision
variance_columns = [
    "var_rate_btwn_prac_season_median",
    "var_rate_w/in_prac_season_median",
    "var_rate_btwn_prac_season_mean",
    "var_rate_w/in_prac_season_mean",
]
for var_df in [combined_var_btwn_df, combined_var_within_df]:
    for col in var_df.columns:
        if not pd.api.types.is_numeric_dtype(var_df[col]):
            continue
        if col in variance_columns:
            var_df[col] = var_df[col].round(7)
        else:
            var_df[col] = var_df[col].round(4)

# Merge into one variance table
combined_var_btwn_df = combined_var_btwn_df.merge(
    combined_var_within_df,
    on=["measure", "season", "pandemic"],
    how="left",
)

read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_variances",
    df=combined_var_btwn_df,
    file_type="csv",
)

# ---------------- RATE RATIOS -----------------------------

for seasonal_group in seasonal_groups:

    print(
        f"7. Total numerator for {seasonal_group['practice_season_df']['season'].iloc[0]} after denominator harmonisation = {seasonal_group['practice_season_df']['numerator_sum'].sum()}, \nTotal denominator for {seasonal_group['practice_season_df']['season'].iloc[0]} after denominator harmonisation = {seasonal_group['practice_season_df']['list_size_initial'].sum()}, \nTotal practices for {seasonal_group['practice_season_df']['season'].iloc[0]} after denominator harmonisation = {seasonal_group['practice_season_df']['practice_pseudo_id'].nunique()}"
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
# Practice level counts used in stat_test.r
read_write(
    read_or_write="write",
    path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/practice_level_counts",
    df=long_df,
    file_type="arrow",
)

# Apply SDC before calculating RRs and RDs
summer["season_df"] = roundmid_any(
    summer["season_df"],
    ["numerator_sum_sum", "list_size_initial_sum", "list_size_count_sum"],
    to=6,
)
non_summer["season_df"] = roundmid_any(
    non_summer["season_df"],
    ["numerator_sum_sum", "list_size_initial_sum", "list_size_count_sum"],
    to=6,
)

combined_seasons_df = calculate_rate_ratios(
    summer["season_df"], non_summer["season_df"], practice_level=False, mp6_input=True
)
rename_map = {
    "numerator_sum_sum_mp6": "num_sum_mp6",
    "list_size_initial_sum_mp6": "list_size_initial_mp6",
    "numerator_sum_sum_mp6_prev_summr": "num_prev_summer_mp6",
    "list_size_initial_sum_mp6_prev_summr": "list_prev_summer_mp6",
    "list_size_count_sum_mp6_prev_summr": "n_practices_prev_summer_mp6",  # n_practices prev summer is the same as n_practices for that winter
    "numerator_sum_sum_mp6_first_summr": "num_first_summer_mp6",
    "list_size_initial_sum_mp6_first_summr": "list_first_summer_mp6",
    "list_size_count_sum_mp6_first_summr": "n_practices_first_summer_mp6",
    "Rate_per_1000_mp6": "rate_/1000_mp6",
    "Rate_per_1000_prev_summr_mp6": "rate_/1000_prev_summer_mp6",
    "Rate_per_1000_first_summr_mp6": "rate_/1000_first_summer_mp6",
}

# Format output table
combined_seasons_df = combined_seasons_df.rename(columns=rename_map)
combined_seasons_df = combined_seasons_df.drop(
    columns=["season_prev_summr", "season_first_summr"]
)
combined_seasons_df = combined_seasons_df.round(4)
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

# Skipping SDC as aggregate median RR with high N is undisclosive
# summer["practice_season_df"] = roundmid_any(summer["practice_season_df"], ["numerator_sum", "list_size_initial", "list_size_count"], to=6)
# non_summer["practice_season_df"] = roundmid_any(non_summer["practice_season_df"], ["numerator_sum", "list_size_initial", "list_size_count"], to=6)

# Calculate practice-level RRs and RDs comparing each season to the two summer baselines (prev summer and first summer)
combined_practice_seasons_df = calculate_rate_ratios(
    summer["practice_season_df"],
    non_summer["practice_season_df"],
    practice_level=True,
    mp6_input=False,
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
yearly_unweighted_results = aggregate_unweighted_rr_results(
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

# Clean and save yearly unweighted RRs
for yearly_df, baseline in zip(yearly_unweighted_results, ["first", "prev"]):
    # Round
    yearly_df = yearly_df.round(4)
    # Save unweighted RRs per year
    yearly_df = yearly_df.rename(columns=rename_map)
    # Apply SDC rounding to counts
    yearly_df = roundmid_any(
        yearly_df,
        [
            "Rate_per_1000_median",
            f"Rate_per_1000_{baseline}_summr_median",
            f"n_practice_{baseline}_summer",
        ],
        to=6,
    )
    read_write(
        read_or_write="write",
        path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_unweighted_yearly_{baseline}_summer",
        df=yearly_df,
        file_type="csv",
    )

## Pandemic period RRs
pandemic_unweighted_results = aggregate_unweighted_rr_results(
    combined_practice_seasons_df,
    ["measure", "season", "pandemic"],
)

# Change n_practices to n_practice-years (count of practices contributing to each season-pandemic period)
rename_map["list_size_count_first_summr_sum"] = "n_practice-years_first_summer"
rename_map["list_size_count_prev_summr_sum"] = "n_practice-years_prev_summer"

# Clean and save pandemic period unweighted RRs
for pandemic_df, baseline in zip(pandemic_unweighted_results, ["first", "prev"]):

    # Save unweighted RRs per pandemic period
    pandemic_df = pandemic_df.rename(columns=rename_map)
    pandemic_df = pandemic_df.round(4)
    pandemic_df = roundmid_any(
        pandemic_df,
        [
            "Rate_per_1000_median",
            f"Rate_per_1000_{baseline}_summr_median",
            f"n_practice-years_{baseline}_summer",
        ],
        to=6,
    )
    read_write(
        read_or_write="write",
        path=f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_unweighted_pandemic_{baseline}_summer",
        df=pandemic_df,
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
