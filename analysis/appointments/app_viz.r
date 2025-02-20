library(ggplot2)
library(dplyr)
library(glue)
library(reshape2)

# Import appointments data
appointments <- read.csv('output/appointments/app_pivot_counts.csv')
appointments$interval_start <- as.Date(appointments$interval_start)

# Heatmap
# Filter out unnecessary columns
intervals <- unique(appointments$interval_start)
for (i in 1:length(intervals)) {
  appointments_filtered <- appointments %>% filter(interval_start == intervals[i])
  appointments_filtered <- appointments_filtered %>% select(-c(interval_start, denominator, Total))
  # Reshape to long format
  df_melted <- melt(appointments_filtered)
  df_prop <- df_melted %>%
    group_by(measure) %>%
      mutate(prop = value / sum(value)) %>%
       ungroup() %>%
          mutate(prop_label = case_when(
              prop > 0.001 ~ scales::percent(prop, accuracy = 0.001),  # Show proportion if > 0.001%
              prop > 0     ~ "<0.001%",  # Label trace values
              TRUE         ~ "0%"       # Ensure zeros display as "0%"
            ))
  ggplot(df_prop, aes(x = measure, y = variable, fill = prop)) +
    geom_tile() +
    scale_fill_gradient(low = "white", high = "red") +
    geom_text(aes(label = prop_label), color = "black", size = 3) +
    labs(title = glue("Measure vs. Appointment Status {intervals[i]}"), x = "Measure", y = "Status") +
    theme(axis.text.x = element_text(angle = 15, vjust = 0.7))
  # Save plot
  ggsave(glue("output/appointments/app_heatmap_{i}.png"), width = 13, height = 6, dpi = 300)
}
