# TODO: 
# Output a few decile plots for practice measures

library(ggplot2)
library(dplyr)
library(glue)

measures <- read.csv('output/patient_measures/processed_patient_measures.csv.gz')
practice_measures <- read.csv('output/practice_measures/processed_practice_measures.csv.gz')

# Function that aggregates timetrends for patient charcteristics (col_name), faceted by another characteristics, & can be filtered to only some population
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
    filter_col <- "none"
  }
  print(group_vars)
  # Summarise by numerator, denominator, and calculate rate per 1000
  df <- df %>%
    group_by(across(all_of(group_vars))) %>%
    summarise(numerator_total = sum(numerator), denominator_total = sum(denominator), measure_rate_per_1000=(sum(numerator)/sum(denominator))*1000, .groups = 'drop')

  write.csv(df, glue("output/{folder}/{main_col}_by_{facet_col}_filter_for_{filter_col}.csv"))
}

# --- Aggregating unstratified appointment and measures data ----------------------------------------------

# Changing date columns to date type
measures$interval_start <- as.Date(measures$interval_start)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# total_app_df = total instances of each measure in interval using valid appointments (start_date == seen_date),
# removing stratification by groupby criteria
aggregate_trends_by_facet(measures, main_col = NULL, facet_col = NULL, filter_col = NULL, folder = "total_measures")

# --- Aggregating measures stratified by patient characteristics ------------------------------------------------

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id

start_index = which(names(measures) == "numerator") + 1
for(col in colnames(measures)[start_index:(length(measures) - 1)]){
  aggregate_trends_by_facet(measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "patient_measures")
}

# --- Aggregating measures stratified by practice characteristics ------------------------------------------------

start_index = which(names(practice_measures) == "numerator") + 1
for(col in colnames(practice_measures)[start_index:length(practice_measures) - 1]){
  aggregate_trends_by_facet(practice_measures, main_col = col, facet_col = NULL, filter_col = NULL, folder = "practice_measures")
}

# --- Aggregating measures stratified by vax status and comorbidities ------------------------------------------------

# Aggregating vax trends by age, no filter
lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, main_col = vax, facet_col = "age", filter_col = NULL, folder = "patient_measures"))

# Aggregating vax trends by age & indication (comorbidity)
for (disease in c("comorbid_chronic_resp", "comorbid_copd", "comorbid_asthma")) {
  lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, main_col = vax, facet_col = "age", filter_col = disease, folder = "patient_measures"))
}

# Aggregating comorbid trends by age
comorbid_any <- c("comorbid_chronic_resp","comorbid_copd", "comorbid_asthma", "comorbid_dm", "comorbid_htn", "comorbid_depres", "comorbid_mh", "comorbid_neuro", "comorbid_immuno")
lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, main_col = comorbid, facet_col = "age", filter_col = NULL, folder = "patient_measures"))

# Aggregating comorbid trends by imd
lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, main_col = comorbid, facet_col = "imd_quintile", filter_col = NULL, folder = "patient_measures"))
