# Run using Rscript analysis/decomposition.r
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval
# --weekly_agg aggregates weekly intervals to yearly
# Depends on round_measures.r

library(dplyr)
library(glue)
library(ggplot2)
library(ggfortify)
source("analysis/utils.r")
source("analysis/parse_args.r")

# Read in CSV file

path <- glue("output/practice_measures_{config$set}{config$appt_suffix}/proc_practice_measures_midpoint6")
data <- read_write("read", path, file_type = "arrow")

# Calculate rate per 1000
data["rate_per_1000_midpoint6_derived"] <- (
  data["numerator_midpoint6"]
  / data["list_size_midpoint6"]
    * 1000
)

# Aggregate to national level by measure (sum practice-level counts)
data <- data %>%
  group_by(measure, interval_start) %>%
  summarise(
    numerator_midpoint6 = sum(numerator_midpoint6, na.rm = TRUE),
    list_size_midpoint6 = sum(list_size_midpoint6, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    rate_per_1000_midpoint6_derived = numerator_midpoint6 / list_size_midpoint6 * 1000
  ) %>%
  arrange(interval_start)

# Iteratively decompose each measure's time series
for (measure_name in unique(data$measure)) {
  measure_data <- filter(data, measure == measure_name)
  
  # Convert to time series object
  start_date <- min(measure_data$interval_start, na.rm = TRUE)
  ts_start <- c(as.integer(format(start_date, "%Y")), as.integer(format(start_date, "%V")))
  ts_data <- ts(measure_data$rate_per_1000_midpoint6_derived, frequency = 52, start = ts_start)
  print(ts_start)
  # Perform time series decomposition
  decomposed <- stl(ts_data, s.window = "periodic")
  
  # Plot the decomposition
  output_path <- glue("output/practice_measures_{config$set}{config$appt_suffix}/decompositions/{measure_name}{ifelse(config$test, '_test', '')}.png")
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)

  p <- autoplot(decomposed) + ggtitle(glue("Decomposition of {measure_name}"))
  ggsave(filename = output_path, plot = p, width = 10, height = 6)

  # Display summary
  summary(decomposed)

  # Save model summary
  summary_path <- glue("output/practice_measures_{config$set}{config$appt_suffix}/decompositions/summary_{measure_name}{ifelse(config$test, '_test', '')}.txt")
  capture.output(summary(decomposed), file = summary_path)
}
