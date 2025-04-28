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
              help = "Uses test data instead of full data"),
  make_option("--RR", action = "store_true", default = FALSE, 
              help = "Uses RR instead of raw rate")
)

# Parse arguments
opt <- parse_args(OptionParser(option_list = option_list))
# Set suffix
suffix <- ""

# Message about test or full
print(if (opt$test) "Using test data" else "Using full data")

# Determine file paths
if (opt$RR) {
  print("Using RR data")
  suffix <- suffix %>% paste0("_RR")

if (opt$test) {
    practice_measures <- read.csv("output/practice_measures/RR_test.csv") %>%
      select(interval_start, measure, practice_pseudo_id, RR)
    practice_measures <- rename(practice_measures, rate_per_1000 = RR)
    suffix <- suffix %>% paste0("_test")

  } else {
    practice_measures <- read_feather(
      "output/practice_measures/RR.arrow",
      col_select = c("interval_start", "measure", "practice_pseudo_id", "RR")
    ) %>%
    rename(rate_per_1000 = RR)
  }
  
} else {
  print("Using raw rate data")
  suffix <- suffix %>% paste0("_raw")

  if (opt$test) {
    practice_measures <- read.csv(glue("output/practice_measures/proc_practice_measures_test.csv.gz"))
    # Generate simulated rate data (since dummy data contains too many 0's to graph)
    practice_measures$numerator <- sample(1:100, nrow(practice_measures), replace = TRUE)  
    practice_measures$list_size <- sample(101:200, nrow(practice_measures), replace = TRUE)  
    practice_measures <- mutate(practice_measures, rate_per_1000=(numerator/list_size)*1000)
    suffix <- suffix %>% paste0("_test")
    
  } else {
    practice_measures <- as.data.frame(read_arrow("output/practice_measures/proc_practice_measures.arrow")) %>%
      mutate(rate_per_1000=(numerator/list_size)*1000)
  }
}

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

# save table
write.csv(practice_deciles, glue("output/practice_measures/decile_table{suffix}.csv"))

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
  not_appts_table = c('GP_ooh_admin','call_from_gp', 'call_from_patient',
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
    labs(title = glue("Decile Charts for {group_name}{suffix}"),
         x = "Interval Start",
         y = "Rate per 1000") +
    facet_wrap(vars(measure), scales = "free_y") +
    theme_bw() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  # Save the plot for this group
  ggsave(glue("output/practice_measures/plots/decile_chart_{group_name}{suffix}.png"),
         plot = plot, width = 20, height = 12, dpi = 400)
}

