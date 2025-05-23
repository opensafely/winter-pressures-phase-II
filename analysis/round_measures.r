# This script rounds the numerator and list size of the processed 
# practice, patient, and ungrouped measures dataframes to midpoint 6.

library(tidyr)
library(glue)
library(dplyr)
library(readr)
library(optparse)
library(arrow)
source("analysis/utils.r")
source("analysis/config.R")

# --------------------- Round processed measures ---------------------

input_path <- glue("output/{group}_measures/proc_{group}_measures")
output_path <- glue("output/{group}_measures/proc_{group}_measures_midpoint6")
df_to_round <- read_write('read', args$test, input_path)

print(glue("Before rounding: {head(df_to_round)}"))
# Select required columns and round their values
round_columns(df = df_to_round, cols_to_round = c('numerator', 'list_size'))
# Save the rounded dataframe to a new CSV file
read_write('write', args$test, output_path, df_to_round)
print(glue("After rounding: {head(df_to_round)}"))