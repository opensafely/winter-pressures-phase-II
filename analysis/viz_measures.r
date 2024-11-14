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

# Function that plots patient charcteristics, grouped by age
plot_trends_by_age <- function (df, col_name) {
  col <- sym(col_name)
  df <- df %>%
  group_by(interval_start, age, !!col) %>%
  summarise(total_app = sum(numerator), .groups = "drop")

  plot_by_age <- ggplot(df, aes(x = interval_start, y = total_app, color = !!col)) +
  geom_line() +
  facet_wrap (~ age, scales = "free_y") +
  labs(title = glue("Apps Over Time by {col_name}"), x = "Time Interval", y = "Appointments", color = col_name)

  ggsave(glue("output/patient_measures/{col_name}_plot_by_age.png"), plot = plot_by_age)
}

# Plot vax trends by age
plot_trends_by_age(measures, "vax_flu_12m")
plot_trends_by_age(measures, "vax_covid_12m")
plot_trends_by_age(measures, "vax_pneum_12m")

# Plot vax trends by age & indication
# Issue: This overruns previous graphs
for (disease in c("comorbid_chronic_resp", "comorbid_copd", "comorbid_asthma")) {
  comorbid <- sym(disease)
  df <- filter(measures, !!comorbid == TRUE)

  for (vax in c("vax_flu_12m", "vax_covid_12m", "vax_pneum_12m")) {
  plot_trends_by_age(df, vax)
  }
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