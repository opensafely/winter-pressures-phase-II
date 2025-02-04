# TODO: 
# Output a few decile plots for practice measures

# ------------ Configuration -----------------------------------------------------------

library(ggplot2)
library(dplyr)
library(glue)
library(optparse)

# Define option list
option_list <- list(
  make_option("--test", action = "store_true", default = TRUE, 
              help = "Uses test data instead of full data")
)
# Parse arguments
opt <- parse_args(OptionParser(option_list = option_list))
if (opt$test) {
  print("Using test data")
  suffix <- "_test"
} else {
  print("Using full data")
  suffix <- ""
}

measures <- read.csv(glue('output/patient_measures/proc_patient_measures{sufix}.csv.gz'))
practice_measures <- read.csv(glue('output/practice_measures/proc_practice_measures{suffix}.csv.gz'))

# ------------ Functions -----------------------------------------------------------

aggregate_trends_by_facet <- function (df, main_col, facet_col, filter_col, folder) {

  # Aggregates timetrends for patient charcteristics (col_name), faceted by another characteristics, & can be filtered to only some population
  # Args:
  #  df: dataframe to be aggregated
  #  main_col: primary characteristic to be aggregated
  #  facet_col: secondary characteristic to be faceted
  #  filter_col: subpopulation to use as filter
  #  folder: folder to save the output
  # Returns:
  #  csv file with aggregated data to be used for downstream analysis and plottting


  # Group by interval_start, measure, main_col, facet_col
  group_vars <- c("interval_start", "measure")

  # Add main_col and facet_col to grouping variables if present
  if (!is.null(main_col)) {
    group_vars <- append(group_vars, main_col)
  } else {
    main_col <- "total"
  }
  if (!is.null(facet_col)) {
    group_vars <- append(group_vars, facet_col)
  } else {
    facet_col <- "none"
  }

  # Filter by filter_col if present
  if (!is.null(filter_col)) {
    df <- filter(df, !!sym(filter_col) == TRUE)
  } else {
    filter_col <- "all"
  }
  print(group_vars)
  # Summarise by numerator, denominator, and calculate rate per 1000
  df <- df %>%
    group_by(across(all_of(group_vars))) %>%
    summarise(numerator_total = sum(numerator), denominator_total = sum(denominator), measure_rate_per_1000=(sum(numerator)/sum(denominator))*1000, .groups = 'drop')

  write.csv(df, glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}.csv"))
}

plot_aggregated_data <- function(df, main_col, facet_col, filter_col, folder) {
  # Plots aggregated data
  # Args:
  #  df: dataframe to be plotted
  #  main_col: primary characteristic to be aggregated
  #  facet_col: secondary characteristic to be faceted
  #  filter_col: subpopulation to use as filter
  #  folder: folder to save the output
  # Returns:
  #  png file with the plot

  # Set default values
  if (is.null(main_col)) {
    main_col <- "total"
  }
  if (is.null(facet_col)) {
    facet_col <- "none"
  }
  if (is.null(filter_col)) {
    filter_col <- "all"
  }

  # Load data
  df <- read.csv(glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}.csv"))

  # Plot
  p <- ggplot(df, aes(x=interval_start, y=measure_rate_per_1000, color=measure, group=measure)) +
    geom_line() +
    geom_point() +
    labs(title=glue("{main_col} by {facet_col} for {filter_col}"), x="Interval Start", y="Rate per 1000")


  # Facet by facet_col if present
  if (main_col != "total") {
    p <- p + facet_wrap(reformulate(main_col))
  }
  # Save plot
  ggsave(glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}.png"), plot=p)
}

# --- Aggregating unstratified appointment and measures data ----------------------------------------------

# Changing date columns to date type
measures$interval_start <- as.Date(measures$interval_start)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# total_app_df = total instances of each measure in interval using valid appointments (start_date == seen_date),
# removing stratification by groupby criteria
aggregate_trends_by_facet(measures, main_col = NULL, facet_col = NULL, filter_col = NULL, folder = "total_measures")
plot_aggregated_data(measures, main_col = NULL, facet_col = NULL, filter_col = NULL, folder = "total_measures")

# --- Aggregating measures stratified by patient characteristics ------------------------------------------------

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id

start_index = which(names(measures) == "numerator") + 1
for(col in colnames(measures)[start_index:(length(measures) - 1)]){
  aggregate_trends_by_facet(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "patient_measures")
  plot_aggregated_data(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "patient_measures")
}

# --- Aggregating measures stratified by practice characteristics ------------------------------------------------
start_index = which(names(practice_measures) == "numerator") + 1
for(col in colnames(practice_measures)[start_index:(length(practice_measures) - 1)]){
  aggregate_trends_by_facet(practice_measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "practice_measures")
  plot_aggregated_data(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "practice_measures")
}

# --- Aggregating measures stratified by vax status and comorbidities ------------------------------------------------

# Aggregating vax trends by age, no filter
#lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, main_col = vax, facet_col = "age", filter_col = NULL, folder = "patient_measures"))

# Aggregating vax trends by age & indication (comorbidity)
#for (disease in c("comorbid_chronic_resp", "comorbid_copd", "comorbid_asthma")) {
#  lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, main_col = vax, facet_col = "age", filter_col = disease, folder = "patient_measures"))
#}

# Aggregating comorbid trends by age
#comorbid_any <- c("comorbid_chronic_resp","comorbid_copd", "comorbid_asthma", "comorbid_dm", "comorbid_htn", "comorbid_depres", "comorbid_mh", "comorbid_neuro", "comorbid_immuno")
#lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, main_col = comorbid, facet_col = "age", filter_col = NULL, folder = "patient_measures"))

# Aggregating comorbid trends by imd
#lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, main_col = comorbid, facet_col = "imd_quintile", filter_col = NULL, folder = "patient_measures"))
