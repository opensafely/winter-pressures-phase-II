library(ggplot2)
library(dplyr)
library(glue)

measures <- read.csv('output/patient_measures/processed_measures.csv.gz')
practice_measures <- read.csv('output/practice_measures/practice_measures.csv.gz')

# Format data
measures$interval_start <- as.Date(measures$interval_start)
all_appnt_df <- filter(measures, measure == 'all_appointments_in_interval')
all_appnt_df <- summarise(group_by(all_appnt_df, interval_start, measure), numerator = sum(numerator), 
                denominator = sum(denominator), total_app=(sum(numerator)/sum(denominator))*1000)

measures <- filter(measures, measure != 'all_appointments_in_interval')
practice_measures$interval_start <- as.Date(practice_measures$interval_start)
total_app_df <- summarise(group_by(measures, interval_start, measure), numerator = sum(numerator), 
                denominator = sum(denominator), total_app=(sum(numerator)/sum(denominator))*1000)

# Create measure of appointments for reason X with prescription [numerator]/ all appointments for reason X [denominator]
index <- which(colnames(measures) == "age")
subgroups <- colnames(measures)[index:length(colnames(measures))]
subgroups <- c(subgroups, "interval_start", "interval_end")

numerators <- c("back_pain_opioid", "chest_inf_abx", "chest_inf_abx")
denominators <- c("back_pain", "chest_inf", "pneum")

"""mapply(function(numerator, denominator){
  measures_df <- data.frame()
  tmp_df <- measures %>%
    filter(measure == numerator | measure == denominator) %>%
    group_by(across(all_of(subgroups))) %>%
    summarise(new_measure = glue("prop_{numerator}"), 
              measure = measure,
              numerator = numerator[measure == numerator],
              denominator = numerator [measure == denominator],
              ratio = numerator/denominator)%>%
    select(- measure)%>%
    rename(measure = new_measure)
  measures_df <- bind_rows(measures_df, tmp_df)
  return(measures_df)
}, numerators, denominators)
"""
back_pain_df <- measures %>%
  filter(measure == "back_pain_opioid" | measure == "back_pain") %>%
  group_by(across(all_of(subgroups))) %>%
  summarise(new_measure = "prop_opioid_back_pain", 
            measure = measure,
            numerator = numerator[measure == "back_pain_opioid"],
            denominator = numerator [measure == "back_pain"],
            ratio = numerator/denominator)%>%
  select(- measure)%>%
  rename(measure = new_measure)

tmp<- bind_rows(measures, back_pain_df)


# Create a list of data frames
data_frames <- list(all_appnt_df = all_appnt_df, total_app_df = total_app_df)
# Loop over each data frame and create/save the plot
for (df_name in names(data_frames)) {
  df <- data_frames[[df_name]]
  plot <- ggplot(df, aes(x = interval_start, y = total_app, color = measure)) +
  geom_line() +  # Add line
  geom_point() +  # Add markers
  labs(title = "Apps Over Time", x = "Time Interval", y = "Appointments per 1000 people")  # Add title and axis labels
  # Save the plot as a PNG file
  ggsave(glue("output/total_measures/{df_name}.png"), plot = plot)
}
write.csv(total_app_df, "output/total_measures/total_app_df.csv")

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id
for(col in colnames(measures)[8:(length(measures) - 1)]){
  df <- summarise(group_by(measures, interval_start, !!sym(col)), total_app=(sum(numerator)/sum(denominator))*1000)
  patient_plot <- ggplot(df, aes(x = interval_start, y = total_app, color = factor(!!sym(col)))) +
    geom_line() +  # Add line
    geom_point() +  # Add markers
    labs(title = glue("Apps Over Time by {col}"), x = "Time Interval", 
    y = "Appointments per 1000 people", color = col)
  ggsave(glue("output/patient_measures/{col}_plot.png"), plot = patient_plot)
}

# Function that plots timetrends for patient charcteristics (col_name), facted by another characteristics, & can be filtered to only some population
plot_trends_by_facet <- function (df, main_col, facet_col = "age", filter_col = NULL) {
  col <- sym(main_col)
  facet <- sym(facet_col)

  if (!is.null(filter_col)) {
    df <- filter(df, !!sym(filter_col) == TRUE)
  }

  df <- df %>%
  group_by(interval_start, !!facet, !!col) %>%
  summarise(app_rate = sum(numerator)/ (sum(denominator)*1000), .groups = "drop")

  plot_by_facet <- ggplot(df, aes(x = interval_start, y = app_rate, color = !!col)) +
  geom_line() +
  geom_point() +
  facet_wrap (as.formula(paste("~", rlang::as_name(facet))), scales = "free_y") +
  labs(title = glue("Apps Over Time by {main_col}, by {facet_col}, limited to {filter_col}"), x = "Time Interval", y = "Appointments per 1000", color = main_col) +
  theme_light() +
  theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5))
    

  if(is.null(filter_col)){
  ggsave(glue("output/patient_measures/{main_col}_plot_by_{facet_col}_filter_by_NULL.png"), plot = plot_by_facet)
  } else {
  ggsave(glue("output/patient_measures/{main_col}_plot_by_{facet_col}_filter_{filter_col}.png"), plot = plot_by_facet)
  }
}

# Plot vax trends by age, no filter
lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) plot_trends_by_facet(measures, vax))

# Plot vax trends by age & indication (comorbidity)
for (disease in c("comorbid_chronic_resp", "comorbid_copd", "comorbid_asthma")) {
  lapply(c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m"), function(vax) plot_trends_by_facet(measures, vax, filter_col = disease))
}

# Plot comorbid trends by age
comorbid_any <- c("comorbid_chronic_resp","comorbid_copd", "comorbid_asthma", "comorbid_dm", "comorbid_htn", "comorbid_depres", "comorbid_mh", "comorbid_neuro", "comorbid_immuno")
lapply(comorbid_any, function(comorbid) plot_trends_by_facet(measures, comorbid))

# Plot comorbid trends by imd
lapply(comorbid_any, function(comorbid) plot_trends_by_facet(measures, comorbid, facet_col = "imd_quintile"))

# Create plots for different practice characteristics
for(col in colnames(practice_measures)[5:length(practice_measures)]){
  df <- summarise(group_by(practice_measures, interval_start, !!sym(col)), total_app=(sum(numerator)/sum(list_size_raw))*1000)
  print(head(df))
  practice_plot <- ggplot(df, aes(x = interval_start, y = total_app, color = factor(!!sym(col)))) +
    geom_line() +  # Add line
    geom_point() +  # Add markers
    labs(title = glue("Apps Over Time by {col}"), x = "Time Interval",
    y = "Appointments per 1000 people", color = col)
  ggsave(glue("output/practice_measures/{col}_plot.png"), plot = practice_plot)
}
