library(ggplot2)
library(dplyr)
library(glue)

measures <- read.csv('output/patient_measures/processed_measures.csv.gz')
practice_measures <- read.csv('output/practice_measures/practice_measures.csv.gz')

# Format data
measures$interval_start <- as.Date(measures$interval_start)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)
total_app_df <- summarise(group_by(measures, interval_start), total_app=sum(numerator))

# Create the line plot using ggplot for total appointments
plot <- ggplot(total_app_df, aes(x = interval_start, y = total_app, group = 1)) +
  geom_line() +  # Add line
  geom_point() +  # Add markers
  labs(title = "Apps Over Time", x = "Time Interval", y = "Appointments")  # Add title and axis labels
# Save the plot as a PNG file
ggsave("output/total_measures/total_app.png", plot = plot)

# Create plots for different patient characteristic
# length - 1 to avoid plot for practice_pseudo_id
for(col in colnames(measures)[8:(length(measures) - 1)]){
  df <- summarise(group_by(measures, interval_start, !!sym(col)), total_app=sum(numerator))
  patient_plot <- ggplot(df, aes(x = interval_start, y = total_app, color = factor(!!sym(col)))) +
    geom_line() +  # Add line
    geom_point() +  # Add markers
    labs(title = glue("Apps Over Time by {col}"), x = "Time Interval", 
    y = "Appointments", color = col)
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
  summarise(total_app = sum(numerator), .groups = "drop")

  plot_by_facet <- ggplot(df, aes(x = interval_start, y = total_app, color = !!col)) +
  geom_line() +
  geom_point() +
  facet_wrap (as.formula(paste("~", rlang::as_name(facet))), scales = "free_y") +
  labs(title = glue("Apps Over Time by {main_col}, by {facet_col}, limited to {filter_col}"), x = "Time Interval", y = "Appointments", color = main_col) +
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

# Create plots for different practice characteristics
for(col in colnames(practice_measures)[5:length(practice_measures)]){
  df <- summarise(group_by(practice_measures, interval_start, !!sym(col)), total_app=sum(numerator))
  practice_plot <- ggplot(df, aes(x = interval_start, y = total_app, color = factor(!!sym(col)))) +
    geom_line() +  # Add line
    geom_point() +  # Add markers
    labs(title = glue("Apps Over Time by {col}"), x = "Time Interval",
    y = "Appointments", color = col)
  ggsave(glue("output/practice_measures/{col}_plot.png"), plot = practice_plot)
}