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
ggsave("output/total_app.png", plot = plot)

# Create plots for different patient characteristic
for(col in colnames(measures)[8:length(measures)]){
  df <- summarise(group_by(measures, interval_start, !!sym(col)), total_app=sum(numerator))
  patient_plot <- ggplot(df, aes(x = interval_start, y = total_app, color = factor(!!sym(col)))) +
    geom_line() +  # Add line
    geom_point() +  # Add markers
    labs(title = glue("Apps Over Time by {col}"), x = "Time Interval", 
    y = "Appointments", color = col)
  ggsave(glue("output/patient_measures/{col}_plot.png"), plot = patient_plot)
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