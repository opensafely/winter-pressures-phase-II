# This script generates decile charts for practice measures.
# USAGE: Rscript analysis/yearly_measures_analysis.r
# Option --test uses test data
# Option --set specifies the measure set (all, sro, resp)
# Option --released uses already released data
# Option --appt restricts measures to those with an appointment in interval
# Option --yearly uses yearly measures data (REQUIRED)

# ------------ Configuration -----------------------------------------------------------

library(ggplot2)
library(dplyr)
library(tidyr)
library(glue)
library(optparse)
library(arrow)
source("analysis/utils.r")
source("analysis/parse_args.r")

# Message about test or full
print(if (config$test) "Using test data" else "Using full data")

# ------------ Pre-processing ----------------------------------------------------

# Determine file paths
input_path <- glue("output/practice_measures_{config$set}{config$appt_suffix}/proc_practice_measures_midpoint6")
practice_measures <- read_write("read", input_path)

if (config$test) {

  # Generate simulated rate data (since dummy data contains too many 0's to graph)
  practice_measures$numerator_midpoint6 <- sample(1:100, nrow(practice_measures), replace = TRUE)
  practice_measures$list_size_midpoint6 <- sample(101:200, nrow(practice_measures), replace = TRUE)
}

# Calculate rate per 1000
practice_measures <- mutate(practice_measures, rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# Temp - filter out non-age measures
practice_measures <- filter(practice_measures, grepl("_age", measure))
print(head(practice_measures$rate_per_1000))
# Filter out any columns with NAs

