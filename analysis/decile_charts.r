# ------------ Configuration -----------------------------------------------------------

library(ggplot2)
library(dplyr)
library(tidyr)
library(glue)
library(optparse)
library(arrow)

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
  practice_measures <- read.csv(glue('output/practice_measures/proc_practice_measures{suffix}.csv.gz'))
} else {
  print("Using full data")
  suffix <- ""
  practice_measures <- as.data.frame(read_arrow("output/practice_measures/proc_practice_measures.arrow"))
  }


practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# ------------ Create decile charts -----------------------------------------------------------

if (opt$test) {
  practice_measures$numerator <- sample(1:100, nrow(practice_measures), replace = TRUE)  
  practice_measures$list_size <- sample(101:200, nrow(practice_measures), replace = TRUE)  
} 
# Create deciles for practice measures
practice_deciles <- practice_measures %>%
  mutate(ratio = numerator/list_size) %>%  # Calculate ratio
  group_by(interval_start, measure) %>%
  summarise(
    d1 = quantile(ratio, 0.1, na.rm = TRUE),
    d2 = quantile(ratio, 0.2, na.rm = TRUE),
    d3 = quantile(ratio, 0.3, na.rm = TRUE),
    d4 = quantile(ratio, 0.4, na.rm = TRUE),
    d5 = quantile(ratio, 0.5, na.rm = TRUE),  # Median
    d6 = quantile(ratio, 0.6, na.rm = TRUE),
    d7 = quantile(ratio, 0.7, na.rm = TRUE),
    d8 = quantile(ratio, 0.8, na.rm = TRUE),
    d9 = quantile(ratio, 0.9, na.rm = TRUE)
  ) %>%
  ungroup() %>%
  pivot_longer(cols = starts_with("d"), names_to = "decile", values_to = "ratio")

# save table
write.csv(practice_deciles, glue("output/practice_measures/decile_table{suffix}.csv"))

# Define line types (d5 gets a dashed line, others are solid)
line_types <- c("d1" = "dashed", "d2" = "dashed", "d3" = "dashed", "d4" = "dashed", 
                "d5" = "solid",  # Median (d5) gets a dashed line
                "d6" = "dashed", "d7" = "dashed", "d8" = "dashed", "d9" = "dashed")
# Define colors (d5 is red, others are black)
line_colors <- c("d1" = "black", "d2" = "black", "d3" = "black", "d4" = "black", 
                 "d5" = "red",  # d5 is red
                 "d6" = "black", "d7" = "black", "d8" = "black", "d9" = "black")

# Plot decile chart
for (m in unique(practice_deciles$measure)) {
  plot <- ggplot(filter(practice_deciles, measure == m), aes(x = interval_start, y = ratio, group = factor(decile),linetype = decile, color = decile)) +
    geom_line() +
    scale_linetype_manual(values = line_types) +  # Apply custom line types
    scale_color_manual(values = line_colors) +  # Apply custom colors
    labs(title = "Decile Chart",
        x = "Interval",
        y = "Value") 
  ggsave(glue("output/practice_measures/plots/decile_chart_{m}{suffix}.png"), plot)
}