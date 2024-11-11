library(ggplot2)
library(dplyr)
library(glue)

measures <- read.csv('output/patient_measures/processed_measures.csv.gz')
practice_measures <- read.csv('output/practice_measures/practice_measures.csv.gz')

# Format data
measures$interval_start <- as.Date(measures$interval_start)
practice_measures$interval_start <- as.Date(practice_measures$interval_start)
total_app_df <- summarise(group_by(measures, interval_start, measure), numerator = sum(numerator), 
                denominator = sum(denominator), total_app=(sum(numerator)/sum(denominator))*1000)
# Create the line plot using ggplot for total appointments
plot <- ggplot(total_app_df, aes(x = interval_start, y = total_app, color = measure)) +
  geom_line() +  # Add line
  geom_point() +  # Add markers
  labs(title = "Apps Over Time", x = "Time Interval", y = "Appointments per 1000 people")  # Add title and axis labels
# Save the plot as a PNG file
ggsave("output/total_measures/total_app.png", plot = plot)
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