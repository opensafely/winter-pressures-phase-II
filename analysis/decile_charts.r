# This script generates charts for visualising rates, RRs and RDs for practice measures.
# USAGE: 
# From codespaces: Rscript analysis/decile_charts.r --params
# From positron: Source("analysis/decile_charts.r") using local params
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval
# --weekly_agg aggregates weekly intervals to yearly
# --y_value choose RR_prev_summr/RD_prev_summr/rate_per_1000_wday charts

# ------------ Configuration -----------------------------------------------------------

library(ggplot2)
library(dplyr)
library(tidyr)
library(glue)
library(optparse)
library(lubridate)
library(arrow)
source("analysis/utils.r")
source("analysis/parse_args.r")

# Message about test or full
print(if (config$test) "Using test data" else "Using full data")

# If running locally in positron using source(), set CLI args manually
if (interactive()) {
  # SET PARAMETERS HERE:
  config$dummy <- FALSE # Set to TRUE to use dummy data folder
  config$rr_plot <- "dotplot"
  config$rate_plot <- "seasonal lineplot"
  config$test <- FALSE
  config$released <- TRUE
  config$set <- "resp"
  config$y_value <- "RR_prev_summr"
  config$practice_measures <- TRUE
  config$practice_subgroup_measures <- FALSE
  config$weekly_agg <- FALSE
  config$yearly <- FALSE
  config$appt <- FALSE

  config <- recompute_config(config)
}

# Use dummy data if developing locally
dummy_folder <- if (config$dummy) "practice_measures_resp_DUMMY/" else ""

# ------------ Generate decile tables ----------------------------------------------------

if (config$released == FALSE){

  # RR PROCESSING
  if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {

    print("Processing rate ratios...")
    input_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/practice_level_RR")
    practice_measures <- read_write("read", input_path)
    print(unique(practice_measures$season))
    if (config$test) {
      practice_measures$RR_prev_summr <- sample(0.5:20, nrow(practice_measures), replace = TRUE)
    }

  } 
  
  # RATES PROCESSING
  else {
    print("Processing rates...")
    input_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/proc_{config$group}_measures")
    practice_measures <- read_write("read", input_path)

    # Round rates
    practice_measures <- practice_measures %>%
      mutate(numerator_midpoint6 = roundmid_any(numerator), list_size_midpoint6 = roundmid_any(list_size))

    config$y_value <- paste0(config$y_value, "_mp6") # Add midpoint suffix to Y_VALUE for plotting
    if (config$test) {
        # Generate simulated rate data (since dummy data contains too many 0's to graph)
        practice_measures$numerator_midpoint6 <- sample(1:100, nrow(practice_measures), replace = TRUE)
        practice_measures$list_size_midpoint6 <- sample(101:200, nrow(practice_measures), replace = TRUE)
    }
    
    # Calculate rate per 1000
    practice_measures <- mutate(practice_measures, rate_per_1000_wday_mp6 = ((numerator_midpoint6 / list_size_midpoint6) * 1000) / wdays_in_interval)
    practice_measures$interval_start <- as.Date(practice_measures$interval_start)


    # If measures are subgrouped, then aggregate up to overall level
    if (config$practice_subgroup_measures) {

      print("Aggregating subgroup measures to overall practice level...")
      # Temp - filter out non-age measures
      practice_measures <- filter(practice_measures, grepl("_age", measure))

      # Aggregate measures-age groups to measure level
      practice_measures <- practice_measures %>%
        group_by(practice_pseudo_id, measure, interval_start) %>%
        summarise(
          numerator_midpoint6 = sum(numerator_midpoint6, na.rm = TRUE),
          list_size_midpoint6 = sum(list_size_midpoint6, na.rm = TRUE)
        ) %>%
        mutate(rate_per_1000_wday_mp6 = ((numerator_midpoint6 / list_size_midpoint6) * 1000) / wdays_in_interval) %>%
        ungroup()

      # Remove "_age" suffix from measure names to match group definitions
      practice_measures <- practice_measures %>%
        mutate(measure = sub("_age$", "", measure))
    }
  }

  print("Creating decile tables...")

  # Create period_date for plotting on x-axis (start of each 2-month period)
  if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {
    practice_measures <- practice_measures %>%
    mutate(
      # Match new year seasons to the proceeding year
      period_year = case_when(
        season %in% c("Jan-Feb", "Mar-Apr") ~ summer_year + 1L,
        TRUE ~ summer_year
      ),
      period_month = case_when(
        season == "Sep-Oct" ~ 9L,
        season == "Nov-Dec" ~ 11L,
        season == "Jan-Feb" ~ 1L,
        season == "Mar-Apr" ~ 3L,
        season == "Jun-Jul" ~ 6L,
        TRUE ~ NA_integer_
      ),
      # start of the 2-month period
      interval_start = make_date(period_year, period_month, 1L)
    )
  }

  grouping_cols <- if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {
    c("season", "interval_start", "measure")
  } else {
    c("interval_start", "measure")
  }

  practice_deciles <- practice_measures %>%
    group_by(across(all_of(grouping_cols))) %>%
    summarise(
      d1 = quantile(!!sym(config$y_value), 0.1, na.rm = TRUE),
      d2 = quantile(!!sym(config$y_value), 0.2, na.rm = TRUE),
      d3 = quantile(!!sym(config$y_value), 0.3, na.rm = TRUE),
      d4 = quantile(!!sym(config$y_value), 0.4, na.rm = TRUE),
      d5 = quantile(!!sym(config$y_value), 0.5, na.rm = TRUE), # Median
      d6 = quantile(!!sym(config$y_value), 0.6, na.rm = TRUE),
      d7 = quantile(!!sym(config$y_value), 0.7, na.rm = TRUE),
      d8 = quantile(!!sym(config$y_value), 0.8, na.rm = TRUE),
      d9 = quantile(!!sym(config$y_value), 0.9, na.rm = TRUE)
    ) %>%
    ungroup() %>%
    pivot_longer(cols = starts_with("d"), names_to = "decile", values_to = config$y_value)

  # Save tables, generating a separate file for each measure
  for (measure in unique(practice_deciles$measure)) {
    measure_data <- practice_deciles %>% filter(measure == !!measure)
    
    read_write("write",
      glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/decile_tables/decile_table_{measure}_{config$y_value}"),
      df = measure_data,
      file_type = "csv"
    )
  }
  print("DECILE TABLES GENERATED")
  
} else if (config$released == TRUE) { # If data is already released, read in the decile tables instead of generating them from raw data

  practice_deciles <- load_decile_table(config)
}

# ------------ Create decile charts -----------------------------------------------------------
print("Creating decile charts...")

result <- process_decile_tables(practice_deciles, config, n_deciles_plot = "all", filter_pandemic = TRUE)

practice_deciles  <- result$decile_table
measure_groups <- result$measure_groups
plots_dir     <- result$plots_dir
line_types    <- result$line_types
line_colors   <- result$line_colors

# Loop over the groups and create plots dynamically
for (group_name in names(measure_groups)) {

  for (season in unique(practice_deciles$season)) {
    print(glue("Creating plot for:{group_name} (Season: {season}) (Y-axis: {config$y_value})..."))

    # Filter measures and deciles for the current group and season
    measures_subset <- measure_groups[[group_name]]
    filtered_deciles <- practice_deciles %>% filter(season == !!season)
    print(head(filtered_deciles))
    # Skip plotting if no measures in this group
    if (length(measures_subset) == 0) {
      print(paste("Skipping plot for", group_name, "(no measures)"))
      next
    }
    if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {
      create_and_save_decile_plot(config$rr_plot, filtered_deciles, group_name, measures_subset, plots_dir, config$y_value, season = season)
    } else {
      create_and_save_decile_plot(config$rate_plot, filtered_deciles, group_name, measures_subset, plots_dir, config$y_value, season = season)
    }
  }
}