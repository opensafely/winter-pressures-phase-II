# This script generates decile charts for practice measures.
# USAGE: Rscript analysis/decile_charts.r
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval
# --weekly_agg aggregates weekly intervals to yearly
# --rr generates charts for rate ratios instead of rates

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
non_appts_table_measures <- FALSE # Set to TRUE to process non-appts table measures (e.g. call_from_gp)
N_DECILES_PLOT <- "all" # Options are "all" to plot all deciles or "light" to plot only key deciles (d1, d3, d5, d7, d9) for clearer visuals

# ------------ Generate decile tables ----------------------------------------------------

if (config$released == FALSE){

  # RR PROCESSING
  if (config$rr) {

    print("Processing rate ratios...")
    input_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/practice_level_RR")
    Y_VALUE <- "RR_prev_summr"
    INTERVALS <- "summer_year"
    print(glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/practice_level_RR"))
    practice_measures <- read_write("read", input_path)

    if (config$test) {
      practice_measures$RR_prev_summr <- sample(0.5:20, nrow(practice_measures), replace = TRUE)
    }

  } 
  
  # RATES PROCESSING
  else {
    print("Processing rates...")
    input_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/proc_{config$group}_measures")
    Y_VALUE <- "rate_per_1000"
    INTERVALS <- "interval_start"
    practice_measures <- read_write("read", input_path)

      if (config$test) {
        # Generate simulated rate data (since dummy data contains too many 0's to graph)
        practice_measures$numerator_midpoint6 <- sample(1:100, nrow(practice_measures), replace = TRUE)
        practice_measures$list_size_midpoint6 <- sample(101:200, nrow(practice_measures), replace = TRUE)
    }
    
    # Calculate rate per 1000
    practice_measures <- mutate(practice_measures, rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000)
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
        mutate(rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
        ungroup()

      # Remove "_age" suffix from measure names to match group definitions
      practice_measures <- practice_measures %>%
        mutate(measure = sub("_age$", "", measure))
    }
  }

  print("Creating decile tables...")
  # Create deciles for practice measures
  practice_deciles <- practice_measures %>%
    group_by(!!sym(INTERVALS), measure) %>%
    summarise(
      d1 = quantile(!!sym(Y_VALUE), 0.1, na.rm = TRUE),
      d2 = quantile(!!sym(Y_VALUE), 0.2, na.rm = TRUE),
      d3 = quantile(!!sym(Y_VALUE), 0.3, na.rm = TRUE),
      d4 = quantile(!!sym(Y_VALUE), 0.4, na.rm = TRUE),
      d5 = quantile(!!sym(Y_VALUE), 0.5, na.rm = TRUE), # Median
      d6 = quantile(!!sym(Y_VALUE), 0.6, na.rm = TRUE),
      d7 = quantile(!!sym(Y_VALUE), 0.7, na.rm = TRUE),
      d8 = quantile(!!sym(Y_VALUE), 0.8, na.rm = TRUE),
      d9 = quantile(!!sym(Y_VALUE), 0.9, na.rm = TRUE)
    ) %>%
    ungroup() %>%
    pivot_longer(cols = starts_with("d"), names_to = "decile", values_to = "value")

  # Save tables, generating a separate file for each measure
  for (measure in unique(practice_deciles$measure)) {
    measure_data <- practice_deciles %>% filter(measure == !!measure)
    
    read_write("write",
      glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/decile_tables/decile_table_{measure}_{Y_VALUE}"),
      df = measure_data,
      file_type = "csv"
    )
  }
  print("DECILE TABLES GENERATED")
  
} else if (config$released == TRUE) { # If data is already released, read in the decile tables instead of generating them from raw data

  print("Reading in released decile tables...")
  # List all measure-specific files
  files <- list.files(glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/decile_tables/"), 
                      full.names = TRUE)

  # Read and combine into one dataframe
  practice_deciles <- files %>%
    lapply(read_csv) %>%
    bind_rows()
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
plots_dir <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/plots{config$test_suffix}")
if (!dir.exists(plots_dir)) {
  dir.create(plots_dir, recursive = TRUE, showWarnings = FALSE)
}

print(practice_deciles)
# Loop over the groups and create plots dynamically
for (group_name in names(measure_groups)) {
  print(paste("Creating plot for:", group_name))
  measures_subset <- measure_groups[[group_name]]
  if (length(measures_subset) == 0) {
    print(paste("Skipping plot for", group_name, "(no measures)"))
    next
  }
  create_and_save_decile_plot(group_name, measures_subset, plots_dir, INTERVALS, Y_VALUE)
  
}