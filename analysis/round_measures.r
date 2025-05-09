# This script rounds the numerator and list size of the processed 
# practice, patient, and ungrouped measures dataframes to midpoint 6.

library(tidyr)
library(glue)
library(dplyr)
library(readr)
library(optparse)
library(arrow)
source("analysis/utils.r")

# --------------------- Configuration ------------------------------------------------

# Define option list
option_list <- list(
  make_option("--test", action = "store_true", default = FALSE, 
              help = "Uses test data instead of full data"),
  make_option("--comorbid", action = "store_true", default = FALSE,
              help = "Uses comorbid data"),
  make_option("--demograph", action = "store_true", default = FALSE,
              help = "Uses demographic data")
)
# Parse arguments
opt <- parse_args(OptionParser(option_list = option_list))

if (opt$test) {
  # Load the data
  suffix <- "_test.csv.gz" 
  comorbid_file <- "proc_patient_measures_test_comorbid.csv.gz"
  read_file <- read.csv     # Assign function reference, not result
  write_file <- write.csv
} else {
  suffix <- ".arrow"
  read_file <- function(path) as.data.frame(read_feather(path))  # wrap in a function to add args
  write_file <- write_feather
  comorbid_file <- "proc_patient_measures_comorbid.arrow"
}


# --------------------- Round processed measures ---------------------

files_to_round = c(
  glue("output/practice_measures/proc_practice_measures{suffix}"),
  glue("output/patient_measures/proc_patient_measures{suffix}"),
  glue("output/ungrouped_measures/proc_ungrouped_measures{suffix}"),
  glue("output/patient_measures/{comorbid_file}")
)

output_files = c(
  glue("output/practice_measures/proc_practice_measures_midpoint6{suffix}"),
  glue("output/patient_measures/proc_patient_measures_midpoint6{suffix}"),
  glue("output/ungrouped_measures/proc_ungrouped_measures_midpoint6{suffix}"),
  glue("output/patient_measures/proc_patient_measures_comorbid_midpoint6{suffix}")
)

# Read in the data
for (idx in c(1:length(files_to_round))) {

  print(glue("Rounding {files_to_round[idx]}"))
  # Read the files
  read_file(files_to_round[idx]) %>%
    # Select required columns and round their values
    round_columns(cols_to_round = c('numerator', 'list_size')) %>%
    # Save the rounded dataframe to a new CSV file
    write_file(output_files[idx])
}