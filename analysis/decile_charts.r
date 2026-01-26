# This script generates decile charts for practice measures.
# USAGE: Rscript analysis/decile_charts.r
# Option --test uses test data
# Option --set specifies the measure set (all, sro, resp)
# Option --RR uses Rate Ratio data
# Option --released uses already released data
# Option --appt restricts measures to those with an appointment in interval
# Option --yearly uses yearly measures data

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

# ------------ Generate decile tables ----------------------------------------------------

if (config$released == FALSE){

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

  if (config$yearly) {

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

  # Create deciles for practice measures
  practice_deciles <- practice_measures %>%
    group_by(interval_start, measure) %>%
    summarise(
      d1 = quantile(rate_per_1000, 0.1, na.rm = TRUE),
      d2 = quantile(rate_per_1000, 0.2, na.rm = TRUE),
      d3 = quantile(rate_per_1000, 0.3, na.rm = TRUE),
      d4 = quantile(rate_per_1000, 0.4, na.rm = TRUE),
      d5 = quantile(rate_per_1000, 0.5, na.rm = TRUE), # Median
      d6 = quantile(rate_per_1000, 0.6, na.rm = TRUE),
      d7 = quantile(rate_per_1000, 0.7, na.rm = TRUE),
      d8 = quantile(rate_per_1000, 0.8, na.rm = TRUE),
      d9 = quantile(rate_per_1000, 0.9, na.rm = TRUE)
    ) %>%
    ungroup() %>%
    pivot_longer(cols = starts_with("d"), names_to = "decile", values_to = "rate_per_1000")

  # Save tables, generating a separate file for each measure
  for (measure in unique(practice_deciles$measure)) {
    measure_data <- practice_deciles %>% filter(measure == !!measure)

    read_write("write",
      glue("output/practice_measures_{config$set}{config$appt_suffix}/decile_tables/decile_table_{measure}_rate_mp6"),
      df = measure_data,
      file_type = "csv"
    )
  }
} else if (config$released == TRUE) {

  # List all measure-specific files
  files <- list.files(glue("output/practice_measures_{config$set}{config$appt_suffix}/decile_tables/"), 
                      full.names = TRUE)

  # Read and combine into one dataframe
  practice_deciles <- files %>%
    lapply(read_csv) %>%
    bind_rows()
}
# ------------ Create decile charts -----------------------------------------------------------
print(head(practice_deciles))
# Define line types
line_types <- c(
  "d1" = "dashed", "d3" = "dashed",
  "d5" = "solid", # Median (d5) is solid
  "d7" = "dashed", "d9" = "dashed"
)

# Define colors
line_colors <- c(
  "d1" = "black", "d3" = "black",
  "d5" = "red", # d5 is red
  "d7" = "black", "d9" = "black"
)

# Define your groups of measures dynamically
if (config$set == "all") {
  measure_groups <- list(
    # Plot 1: Appointments table measures
    appts_table = c(
      "CancelledbyPatient", "CancelledbyUnit", "DidNotAttend", "Waiting",
      "follow_up_app", "seen_in_interval", "start_in_interval"
    ),
    # Plot 2: Other measures
    not_appts_table = c(
      "call_from_gp", "call_from_patient",
      "emergency_care", "online_consult", "secondary_referral",
      "tele_consult", "vax_app", "vax_app_covid", "vax_app_flu"
    )
  )
} else if (config$set == "sro") {
  sro_measures <- append(config$prioritized, "sro_prioritized")
  sro_measures <- append(sro_measures, "sick_notes")
  measure_groups <- list(
    # Plot 1: De-prioritized measures
    deprioritized = append(config$deprioritized, "sro_deprioritized"),
    # Plot 2: Prioritized measures
    prioritized = sro_measures
  )
} else if (config$set == "resp") {
  measure_groups <- list(
    # Plot 1: Flu/RSV/COVID measures
    flu_rsv_covid = c(
      "flu_sensitive", "rsv_sensitive", "covid_sensitive",
      "flu_specific", "rsv_specific", "covid_specific"
    ),
    # Plot 2: Other measures
    other = c(
      "ili", "overall_resp_sensitive", "secondary_referral", "secondary_appt"
    )
  )
}

# Update measure names if restricting to appts in interval
if (config$appt) {
  for (group_name in names(measure_groups)) {
    measure_groups[[group_name]] <- paste0("appt_", measure_groups[[group_name]])
  }
}

# Setup output directory
suffix = ""
suffix <- if (config$yearly) paste(suffix, "_yearly") else suffix
suffix <- if (config$test) paste(suffix, "_test") else suffix
plots_dir <- glue("output/practice_measures_{config$set}{config$appt_suffix}/plots")
if (!dir.exists(plots_dir)) {
  dir.create(plots_dir, recursive = TRUE, showWarnings = FALSE)
}
print(practice_deciles)
# Loop over the groups and create plots dynamically
for (group_name in names(measure_groups)) {
  measures_subset <- measure_groups[[group_name]]
  create_and_save_decile_plot(group_name, measures_subset, plots_dir, suffix)
}