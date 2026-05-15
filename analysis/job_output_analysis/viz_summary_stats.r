# This script visualises and summarises the RR tables produced by normalization.py
# USAGE: Rscript analysis/job_output_analysis/viz_summary_stats.r
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval

library(dplyr)
library(ggplot2)
library(stringr)
source("analysis/utils.r")
source("analysis/parse_args.r")

# -------- WEIGHTED (NATIONAL) SUMMARY STATISTICS --------

summary_results_df <- read_write("read", glue("output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/Results_weighted"), file_type = "csv")


