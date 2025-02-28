library(ggplot2)
library(dplyr)
library(glue)
library(reshape2)
library(scales)
library(tidyr)

# Import appointments data
appointments <- read.csv('output/appointments/app_pivot_counts.csv')
appointments$interval_start <- as.Date(appointments$interval_start)

# ---- Overall heatmap ----------------------------------------------------------------
# Aggregate data across all intervals
appointments_filtered <- appointments %>% select(-c(interval_start, denominator, Total))
appointments_filtered <- appointments_filtered %>% 
  group_by(measure) %>% 
  summarise_all(sum)
# Reshape to long format
df_melted <- melt(appointments_filtered)
# Compute proportions and labels
df_prop <- df_melted %>%
  group_by(measure) %>%
  mutate(
    prop = value / sum(value),
    prop_label = case_when(
      prop > 0.001 ~ glue("{value} ({scales::percent(prop, accuracy = 0.1)})"),  # Show count + proportion if > 0.1%
      prop > 0     ~ glue("{value} (<0.001%)"),  # Show "<0.1%" for trace values
      TRUE         ~ "0 (0%)"  # Ensure zeros display as "0 (0%)"
    )
  ) %>%
  ungroup()
# Heatmap
ggplot(df_prop, aes(x = measure, y = variable, fill = prop)) +
  geom_tile() +
  scale_fill_gradient(low = "white", high = "red", name = "% of column") +
  geom_text(aes(label = prop_label), color = "black", size = 3) +
  labs(title = "Measure vs. Appointment Status (Overall)", x = "Measure", y = "Status") +
  theme(axis.text.x = element_text(angle = 10, vjust = 0.7, size = 10))
# Save plot
ggsave("output/appointments/app_heatmap_overall.png", width = 16.5, height = 6, dpi = 300)

# ---- Per interval heatmaps ----------------------------------------------------------------
# Filter out unnecessary columns
intervals <- unique(appointments$interval_start)
for (i in 1:length(intervals)) {
  appointments_filtered <- appointments %>% filter(interval_start == intervals[i])
  appointments_filtered <- appointments_filtered %>% select(-c(interval_start, denominator, Total))
  # Reshape to long format
  df_melted <- melt(appointments_filtered)
  # Compute proportions and labels
  df_prop <- df_melted %>%
    group_by(measure) %>%
    mutate(
      prop = value / sum(value),
      prop_label = case_when(
        prop > 0.001 ~ glue("{value} ({scales::percent(prop, accuracy = 0.1)})"),  # Show count + proportion if > 0.1%
        prop > 0     ~ glue("{value} (<0.001%)"),  # Show "<0.1%" for trace values
        TRUE         ~ "0 (0%)"  # Ensure zeros display as "0 (0%)"
      )
    ) %>%
    ungroup()
  ggplot(df_prop, aes(x = measure, y = variable, fill = prop)) +
    geom_tile() +
    scale_fill_gradient(low = "white", high = "red", name = "% of column") +
    geom_text(aes(label = prop_label), color = "black", size = 3) +
    labs(title = glue("Measure vs. Appointment Status {intervals[i]}"), x = "Measure", y = "Status") +
    theme(axis.text.x = element_text(angle = 10, vjust = 0.7, size = 10))
  # Save plot
  ggsave(glue("output/appointments/app_heatmap_{i}.png"), width = 16.5, height = 6, dpi = 300)
}
