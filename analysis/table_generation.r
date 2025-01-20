# TODO: 
# Output a few representative plots for practice measures
# Fix comorbidities and vax status tables

library(ggplot2)
library(dplyr)
library(glue)

measures <- read.csv('output/patient_measures/processed_patient_measures.csv.gz')
practice_measures <- read.csv('output/practice_measures/processed_practice_measures.csv.gz')

# --- Aggregating unstratified appointment and measures data ----------------------------------------------

# Changing date columns to date type
measures$interval_start <- as.Date(measures$interval_start)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# total_app_df = total instances of each measure in interval using valid appointments (start_date == seen_date),
# removing stratification by groupby criteria
total_app_df <- summarise(group_by(measures, interval_start, measure), numerator = sum(numerator), 
                denominator = sum(denominator), total_app=(sum(numerator)/sum(denominator))*1000)

write.csv(total_app_df, "output/total_measures/total_app_df.csv")

# --- Aggregating measures stratified by patient characteristics ------------------------------------------------

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id
for(col in colnames(measures)[8:(length(measures) - 1)]){
  df <- summarise(group_by(measures, interval_start, measure, !!sym(col)), total_app=(sum(numerator)/sum(denominator))*1000)
  write.csv(df, glue("output/patient_measures/{col}_df.csv"))
}

# --- Aggregating measures stratified by practice characteristics ------------------------------------------------

for(col in colnames(practice_measures)[5:length(practice_measures)]){
  df <- summarise(group_by(practice_measures, interval_start, measure, !!sym(col)), total_app=(sum(numerator)/sum(list_size_raw))*1000)
  write.csv(df, glue("output/practice_measures/{col}_df.csv"))
}

# --- Aggregating measures stratified by vax status and comorbidities ------------------------------------------------

# Function that aggregates timetrends for patient charcteristics (col_name), facted by another characteristics, & can be filtered to only some population
aggregate_trends_by_facet <- function (df, main_col, facet_col = "age", filter_col = NULL) {
  col <- sym(main_col)
  facet <- sym(facet_col)

  if (!is.null(filter_col)) {
    df <- filter(df, !!sym(filter_col) == TRUE)
  }

  df <- df %>%
    group_by(interval_start, !!facet, !!col) %>%
    summarise(app_rate = sum(numerator)/ (sum(denominator)*1000), .groups = "drop")

  write.csv(df, glue("output/patient_measures/{main_col}_plot_by_{facet_col}_filter_{filter_col}.csv"))
}

# Aggregating vax trends by age, no filter
lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, vax))

# Aggregating vax trends by age & indication (comorbidity)
for (disease in c("comorbid_chronic_resp", "comorbid_copd", "comorbid_asthma")) {
  lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) aggregate_trends_by_facet(measures, vax, filter_col = disease))
}

# Aggregating comorbid trends by age
comorbid_any <- c("comorbid_chronic_resp","comorbid_copd", "comorbid_asthma", "comorbid_dm", "comorbid_htn", "comorbid_depres", "comorbid_mh", "comorbid_neuro", "comorbid_immuno")
lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, comorbid))

# Aggregating comorbid trends by imd
lapply(comorbid_any, function(comorbid) aggregate_trends_by_facet(measures, comorbid, facet_col = "imd_quintile"))
