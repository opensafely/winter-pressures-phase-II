
# ------------ Configuration -------------------------------------------------------

library(ggplot2)
library(dplyr)
library(glue)
library(optparse)
library (arrow)

# Define option list
option_list <- list(
  make_option("--test", action = "store_true", default = FALSE, 
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

# ------------- Read in files ------------------------------------------------------

if (opt$test) {
  measures <- read.csv("output/ungrouped_measures/proc_ungrouped_measures_test.csv.gz")
  # measures <- read.csv("output/patient_measures/proc_patient_measures_test.csv.gz")
  # measures <- read.csv("output/patient_measures/proc_patient_measures_test_comorbid.csv.gz")
} else {
  measures <- as.data.frame(read_arrow("output/ungrouped_measures/proc_ungrouped_measures.arrow"))
  # measures <- as.data.frame(read_arrow("output/patient_measures/proc_patient_measures*.arrow"))
  # measures <- as.data.frame(read_arrow("output/patient_measures/proc_patient_measures_comorbid*.arrow"))
}


# ------------ Functions -----------------------------------------------------------

aggregate_trends_by_facet <- function (df, main_col, facet_col, filter_col, folder, suffix) {

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
    summarise(numerator_total = sum(numerator), list_size_total = sum(list_size), measure_rate_per_1000=(sum(numerator)/sum(list_size))*1000, .groups = 'drop')

  write.csv(df, glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}{suffix}.csv"))
}

plot_aggregated_data <- function(df, main_col, facet_col, filter_col, folder, suffix) {
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
  df <- read.csv(glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}{suffix}.csv"))

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
  ggsave(glue("output/{folder}/plots/{main_col}_by_{facet_col}_filter_for_{filter_col}{suffix}.png"), plot=p)
}


calculate_stats <- function(df, main_col = NULL, folder, suffix = suffix){
  
  if(is.null(main_col)){
    stats_df<- df %>% 
      mutate(measure_rate_per_1000 = (numerator/ list_size)*1000) %>%
      group_by(measure) %>%
      summarise(numerator_total = sum(numerator), list_size_total = sum(list_size), 
                measure_rate_per_1000=(sum(numerator)/sum(list_size))*1000,
                min = min(measure_rate_per_1000), max= max(measure_rate_per_1000),
                avg = mean(measure_rate_per_1000), median = median(measure_rate_per_1000),
                IQR(measure_rate_per_1000), .groups = 'drop')
    
    write.csv(stats_df, glue("output/{folder}/plots/summary_stats{suffix}.csv"))
  } else {
  stats_df<- df %>% 
    mutate(measure_rate_per_1000 = (numerator/ list_size)*1000) %>%
    group_by(measure, main_col) %>%
    summarise(numerator_total = sum(numerator), list_size_total = sum(list_size), 
              measure_rate_per_1000=(sum(numerator)/sum(list_size))*1000,
              min = min(measure_rate_per_1000), max= max(measure_rate_per_1000),
              avg = mean(measure_rate_per_1000), median = median(measure_rate_per_1000),
              IQR(measure_rate_per_1000), .groups = 'drop')
  
  write.csv(stats_df, glue("output/{folder}/plots/summary_stats_{main_col}_{suffix}.csv"))
  }
  
}



# --- Process and produce summary statistics ----------------------------------------------

# Changing date columns to date type
measures$interval_start <- as.Date(measures$interval_start)

# --- Create ungrouped data and plots -----------------------------------------------------
aggregate_trends_by_facet(measures, main_col = NULL, facet_col = NULL, filter_col = NULL, folder = "ungrouped_measures", suffix)
plot_aggregated_data(measures, main_col = NULL, facet_col = NULL, filter_col = NULL, folder = "ungrouped_measures", suffix)
calculate_stats(measures, main_col = NULL, folder = "ungrouped_measures", suffix)


# --- Aggregating measures stratified by patient characteristics ------------------------------------------------

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id

# start_index = which(names(measures) == "numerator") + 1
# for(col in colnames(measures)[start_index:(length(measures) - 1)]){
#   aggregate_trends_by_facet(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "patient_measures", suffix)
#   plot_aggregated_data(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "patient_measures", suffix)
#   calculate_stats(measures, main_col = col, folder = "patient_measures", suffix)
# }

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
