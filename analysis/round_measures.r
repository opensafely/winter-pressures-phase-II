# This script rounds the numerator and list size of the processed
# practice, patient, and ungrouped measures dataframes to midpoint 6.
# Run using Rscript analysis/round_measures.r
# Option --comorbid_measures/demograph_measures/practice_measures to choose which type of measures to process
# Option --test flag to run a lightweight test with a single date
# Option --set all/sro/resp to choose which set of measures to process
# Option --yearly flag to process only yearly measures

library(tidyr)
library(glue)
library(readr)
library(optparse)
library(arrow)
library(dplyr)
library(lubridate)
library(purrr)
source("analysis/utils.r")
source("analysis/parse_args.r")

# --------------------- Round processed measures ---------------------
print(config$group)
print(config$set)
print(config$appt_suffix)
input_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}/proc_{config$group}_measures")
output_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}/proc_{config$group}_measures_midpoint6")

df_to_round <- read_write("read", input_path)
df_to_round <- tibble(df_to_round)
print("Before rounding:")
print(head(df_to_round))

# Select required columns and round their values
df_to_round <- round_columns(df = df_to_round, cols_to_round = c("numerator", "list_size"))
# Save the rounded dataframe to a new CSV file
print("After rounding:")
print(head(df_to_round))

read_write("write", output_path, df = df_to_round)
