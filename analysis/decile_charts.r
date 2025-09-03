# This script generates decile charts for practice measures.
# USAGE: Rscript analysis/decile_charts.r
# Option --test uses test data
# Option --RR uses Rate Ratio data

# ------------ Configuration -----------------------------------------------------------

library(ggplot2)
library(dplyr)
library(tidyr)
library(glue)
library(optparse)
library(arrow)
source("analysis/utils.r")
source("analysis/config.r")

# Message about test or full
print(if (args$test) "Using test data" else "Using full data")

# Determine file paths
practice_measures <- read_write('read', 'output/practice_measures/proc_practice_measures_midpoint6')

if (args$test) {
  
  # Generate simulated rate data (since dummy data contains too many 0's to graph)
  practice_measures$numerator_midpoint6 <- sample(1:100, nrow(practice_measures), replace = TRUE)  
  practice_measures$list_size_midpoint6 <- sample(101:200, nrow(practice_measures), replace = TRUE)  
  
}

# Calculate rate per 1000
practice_measures <- mutate(practice_measures, rate_per_1000=(numerator_midpoint6/list_size_midpoint6)*1000)

practice_measures$interval_start <- as.Date(practice_measures$interval_start)

# ------------ Create decile charts -----------------------------------------------------------

print(head(practice_measures))
# Create deciles for practice measures
practice_deciles <- practice_measures %>%
  group_by(interval_start, measure) %>%
  summarise(
    d1 = quantile(rate_per_1000, 0.1, na.rm = TRUE),
    d2 = quantile(rate_per_1000, 0.2, na.rm = TRUE),
    d3 = quantile(rate_per_1000, 0.3, na.rm = TRUE),
    d4 = quantile(rate_per_1000, 0.4, na.rm = TRUE),
    d5 = quantile(rate_per_1000, 0.5, na.rm = TRUE),  # Median
    d6 = quantile(rate_per_1000, 0.6, na.rm = TRUE),
    d7 = quantile(rate_per_1000, 0.7, na.rm = TRUE),
    d8 = quantile(rate_per_1000, 0.8, na.rm = TRUE),
    d9 = quantile(rate_per_1000, 0.9, na.rm = TRUE)
  ) %>%
  ungroup() %>%
  pivot_longer(cols = starts_with("d"), names_to = "decile", values_to = "rate_per_1000")

# Save tables, generating a separate file for each measure
for (measure in unique(practice_deciles$measure)) {

  measure_data <- practice_deciles %>% filter(measure == !!measure)

  read_write('write', 
    glue("output/practice_measures/decile_tables/decile_table_{measure}_rate_mp6"), 
    df = measure_data,
    file_type = 'csv')
}

# Define line types
line_types <- c("d1" = "dashed", "d3" = "dashed",  
                "d5" = "solid",  # Median (d5) is solid
                "d7" = "dashed", "d9" = "dashed")

# Define colors
line_colors <- c("d1" = "black", "d3" = "black", 
                 "d5" = "red",  # d5 is red
                 "d7" = "black", "d9" = "black")

# Define your groups of measures dynamically
measure_groups <- list(
  # Plot 1: Appointments table measures
  appts_table = c('CancelledbyPatient', 'CancelledbyUnit', 'DidNotAttend', 'Waiting', 
                  'follow_up_app', 'seen_in_interval', 'start_in_interval'),  
  # Plot 2: Other measures
  not_appts_table = c('call_from_gp', 'call_from_patient',
                      'emergency_care', 'online_consult', 'secondary_referral',
                      'tele_consult', 'vax_app', 'vax_app_covid', 'vax_app_flu')
)

# Loop over the groups and create plots dynamically
for (group_name in names(measure_groups)) {
  measures_subset <- measure_groups[[group_name]]
  
  # Create the plot for this group
  plot <- ggplot(filter(practice_deciles, measure %in% measures_subset), 
                 aes(x = interval_start, y = rate_per_1000, 
                     group = factor(decile),
                     linetype = decile,
                     color = decile)) +
    geom_line() +
    scale_linetype_manual(values = line_types) + 
    scale_color_manual(values = line_colors) + 
    labs(title = glue("Decile Charts for {group_name}_rate_mp6"),
         x = "Interval Start",
         y = "Rate per 1000") +
    facet_wrap(vars(measure), scales = "free_y") +
    theme_bw() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  # Save the plot for this group
  suffix <- if (args$test) "_test" else ""
  ggsave(glue("output/practice_measures/plots/decile_chart_{group_name}_rate_mp6{suffix}.png"),
         plot = plot, width = 20, height = 12, dpi = 400)
}

