# Run using Rscript analysis/decomposition.r
# Options
# --practice_measures/comorbid_measures/demograph_measures
# --set: all/sro/resp
# --test: (True/False)
# Depends on round_measures.r

library(dplyr)
library(glue)
library(ggplot2)
library(ggfortify)
source("analysis/utils.r")
source("analysis/config.r")

# Read in CSV file

path <- glue("output/practice_measures_{args$set}{args$appt_suffix}/proc_practice_measures_midpoint6")
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

data <- filter(data, measure == unique(data$measure)[1]) # Select first measure for decomposition example

# Convert to time series object
start_date <- min(data$interval_start, na.rm = TRUE)
ts_start <- c(as.integer(format(start_date, "%Y")), as.integer(format(start_date, "%m")))
ts_data <- ts(data$rate_per_1000_midpoint6_derived, frequency = 52, start = ts_start)

# Perform time series decomposition
decomposed <- stl(ts_data, s.window = "periodic") # periodic = classical decomoposition

# Plot the decomposition. Use ggplot autoplot when available (returns a ggplot object);
output_path <- glue("output/practice_measures_{args$set}{args$appt_suffix}/national_decomposition_plot{ifelse(args$test, '_test', '')}.png")

p <- autoplot(decomposed)
ggsave(filename = output_path, plot = p, width = 10, height = 6)

# Access individual components
trend <- decomposed$trend
seasonal <- decomposed$seasonal
random <- decomposed$random

# Display summary
summary(decomposed)
