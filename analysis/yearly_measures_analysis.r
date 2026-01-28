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
input_path <- glue("output/practice_measures_{config$set}{config$appt_suffix}{config$yearly_suffix}/proc_practice_measures_midpoint6")
practice_measures <- read_write("read", input_path)

if (config$test) {

  # Generate simulated rate data (since dummy data contains too many 0's to graph)
  practice_measures$numerator_midpoint6 <- sample(1:100, nrow(practice_measures), replace = TRUE)
  practice_measures$list_size_midpoint6 <- sample(101:200, nrow(practice_measures), replace = TRUE)
}

# Calculate rate per 1000
practice_measures <- mutate(practice_measures, rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# Temp - filter out non-age or region measures
practice_measures <- filter(practice_measures, grepl("_age|_region", measure))

# Filter out any columns with NAs
practice_measures <- Filter(function(x)!all(is.na(x)), practice_measures)

# ------------ Generate rate zero summaries ----------------------------------------------------

# Create lookup table for which practices have rates of 0
practice_measures_agg_rates <- practice_measures %>%
  group_by(practice_pseudo_id, measure, interval_start) %>%
  summarise(
    numerator_midpoint6 = sum(numerator_midpoint6, na.rm = TRUE),
    list_size_midpoint6 = sum(list_size_midpoint6, na.rm = TRUE),
  ) %>%
  mutate(rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
  mutate(rate_zero = ifelse(rate_per_1000 == 0, "rate_zero", "rate_nonzero")) %>%
  ungroup()

# Set some rates to zero for testing
if (config$test) {
  random_indices <- sample(1:nrow(practice_measures_agg_rates), size = floor(0.1 * nrow(practice_measures_agg_rates)))
  practice_measures_agg_rates$numerator_midpoint6[random_indices] <- 0
  practice_measures_agg_rates$rate_per_1000[random_indices] <- 0
  practice_measures_agg_rates$rate_zero[random_indices] <- "rate_zero"
}

# Join rate zero info back to main dataframe
practice_measures <- practice_measures %>%
  left_join(
    practice_measures_agg_rates %>%
      select(practice_pseudo_id, measure, interval_start, rate_zero),
    by = c("practice_pseudo_id", "measure", "interval_start")
  )

# Generate plots and tables of list_sizes by rate_zero status
summarise_demographics_rate_zero(practice_measures, "age")
summarise_demographics_rate_zero(practice_measures, "region")

# Export summary table of the total number and pct of practices with zero rates for each measure
practice_measures_rate_zero_summary <- practice_measures_agg_rates %>%
  group_by(measure, interval_start, rate_zero) %>%
  summarise(
    num_practices = n_distinct(practice_pseudo_id),
    numerator_midpoint6 = sum(numerator_midpoint6, na.rm = TRUE),
    list_size_midpoint6 = sum(list_size_midpoint6, na.rm = TRUE),
  ) %>%
  mutate(rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
  mutate(pct_practices = (num_practices / sum(num_practices)) * 100) %>%
  ungroup()

output_summary_path <- glue("output/practice_measures_{config$set}{config$appt_suffix}{config$yearly_suffix}/measure_rate_zero_summary{config$test_suffix}.csv")
read_write("write", output_summary_path, df = practice_measures_rate_zero_summary, file_type = "csv")