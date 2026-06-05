# This script generates decile charts for practice measures.
# USAGE: Rscript analysis/decile_charts.r
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval
# --weekly_agg aggregates weekly intervals to yearly
# --y_value choose RR_prev_summr/RD_prev_summr/rate_per_1000 charts

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
non_appts_table_measures <- FALSE # Set to TRUE to process non-appts table measures (e.g. call_from_gp)
N_DECILES_PLOT <- "all" # Options are "all" to plot all deciles or "light" to plot only key deciles (d1, d3, d5, d7, d9) for clearer visuals
LOCAL <- TRUE # Set to true when working locally
FILTER_PANDEMIC <- TRUE # Set to true to filter out 2020, 2021

if (LOCAL) {
  print("Using local data - SET PARAMETERS HERE:")
  DUMMY <- FALSE # Set to TRUE to use dummy data folder
  config$test <- FALSE
  config$released <- TRUE
  config$set <- "resp"
  config$y_value <- "rate_per_1000_mp6"
  config$practice_measures <- TRUE
  config$practice_subgroup_measures <- FALSE
  config$weekly_agg <- FALSE
  config$yearly <- FALSE
  config$appt <- FALSE
  config <- recompute_config(config)
}

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
    practice_measures <- mutate(practice_measures, rate_per_1000_mp6 = (numerator_midpoint6 / list_size_midpoint6) * 1000)
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
        mutate(rate_per_1000_mp6 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
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

  print("Reading in released decile tables...")
  
  # Use dummy data if in development mode
  dummy_folder <- if (DUMMY) "practice_measures_resp_DUMMY/" else ""
  metric_file_suffix <- glue("_{config$y_value}{config$test_suffix}\\.csv$")
  file_pattern <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/{dummy_folder}decile_tables/")

  # List all measure-specific files
  files <- list.files(
    file_pattern,
    pattern = metric_file_suffix,
    full.names = TRUE
  )

  # Read and combine into one dataframe
  practice_deciles <- files %>%
    lapply(read_csv) %>%
    bind_rows()

  if (config$y_value == "rate_per_1000_mp6"){
    if ("rate_per_1000" %in% colnames(practice_deciles)) {
      practice_deciles <- practice_deciles %>% rename(rate_per_1000_mp6 = rate_per_1000)
    }
  }
}

# ------------ Create decile charts -----------------------------------------------------------
print("Creating decile charts..."
)
# Define line types
line_types <- c(
  "d1" = "dotted", "d3" = "dashed",
  "d5" = "solid", # Median (d5) is solid
  "d7" = "dashed", "d9" = "dotted"
)

# Define colors
line_colors <- c(
  "d1" = "black", "d3" = "black",
  "d5" = "red", # d5 is red
  "d7" = "black", "d9" = "black"
)

# Add additional deciles for yearly data
if (N_DECILES_PLOT == "all") {
  line_types <- c(line_types, "d2" = "dashed", "d4" = "dashed", "d6" = "dashed", "d8" = "dashed")
  line_colors <- c(line_colors, "d2" = "black", "d4" = "black", "d6" = "black", "d8" = "black")
} 

# Define your groups of measures dynamically
print("Defining measure groups for plotting...")
df_measures <- practice_deciles %>% select(measure) %>% distinct()
measure_groups <- list()
if ((config$set == "resp") | (config$set == "appts_table")) {

  measure_groups[[config$set]] <- config$measures_list[[config$set]]
  # Filter out config list of measures to get remaining measures
  measure_groups[["other"]] <- setdiff(df_measures$measure, config$measures_list[[config$set]])

  # Remove "other" group if empty
  if (length(measure_groups[["other"]]) == 0) {
    measure_groups[["other"]] <- NULL 
  }

} else if (config$set == "sro") {

  sro_measures <- append(config$prioritized, "sro_prioritized")
  sro_measures <- append(sro_measures, "sick_notes")
  measure_groups <- list(
    # Plot 1: De-prioritized measures
    deprioritized = append(config$deprioritized, "sro_deprioritized"),
    # Plot 2: Prioritized measures
    prioritized = sro_measures
  )
} 

# Update measure names if restricting to appts in interval
if (config$appt) {
  for (group_name in names(measure_groups)) {
    measure_groups[[group_name]] <- paste0("appt_", measure_groups[[group_name]])
  }
}

# Setup output directory
plots_dir <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/{dummy_folder}plots{config$test_suffix}")
if (!dir.exists(plots_dir)) {
  dir.create(plots_dir, recursive = TRUE, showWarnings = FALSE)
}

# Filter out rows with NA season before plotting
print(practice_deciles)


# Loop over the groups and create plots dynamically
for (group_name in names(measure_groups)) {

  # Loop over each season, filtering the decile table each time
  if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {
    practice_deciles <- practice_deciles %>% filter(!is.na(season)) 
  }
  else{
    # Add season column with "all" values for rate measures to avoid issues
    practice_deciles$season <- "all" 
  }
  for (season in unique(practice_deciles$season)) {
    print(glue("Creating plot for:{group_name} (Season: {season}) (Y-axis: {config$y_value})..."))

    # Filter measures and deciles for the current group and season
    measures_subset <- measure_groups[[group_name]]
    filtered_deciles <- practice_deciles %>% filter(season == !!season)
    print(filtered_deciles$interval_start)
    # Skip plotting if no measures in this group
    if (length(measures_subset) == 0) {
      print(paste("Skipping plot for", group_name, "(no measures)"))
      next
    }
    if (config$y_value == "RR_prev_summr" | config$y_value == "RD_prev_summr") {
      create_and_save_decile_plot("dotplot", filtered_deciles, group_name, measures_subset, plots_dir, config$y_value, season = season)
    } else {
      create_and_save_decile_plot("seasonal lineplot", filtered_deciles, group_name, measures_subset, plots_dir, config$y_value, season = season)
    }
  }
}