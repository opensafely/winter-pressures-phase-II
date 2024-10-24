library(ggplot2)
library(dplyr)
library(glue)

# Import appointments data
appointments <- read.csv('output/appointments/app_measures.csv.gz')
appointments$interval_start <- as.Date(appointments$interval_start)
appointments$interval_end <- as.Date(appointments$interval_end)

# Grouping into broader completed/uncompleted appointment categories using mutate and case_when
appointments <- appointments %>%
  mutate(
    category = case_when(
      grepl("start_and_reasonable_seen_(DidNotAttend|Requested|Blocked|Waiting|CancelledbyPatient|CancelledbyUnit|CancelledbyOtherService|NoAccessVisit|CancelledDueToDeath)", measure) ~ "start_and_reasonable_seen_Uncompleted",
      grepl("seen_and_reasonable_start_(DidNotAttend|Requested|Blocked|Waiting|CancelledbyPatient|CancelledbyUnit|CancelledbyOtherService|NoAccessVisit|CancelledDueToDeath)", measure) ~ "seen_and_reasonable_start_Uncompleted",
      grepl("null_start_(DidNotAttend|Requested|Blocked|Waiting|CancelledbyPatient|CancelledbyUnit|CancelledbyOtherService|NoAccessVisit|CancelledDueToDeath)", measure) ~ "null_start_Uncompleted",
      grepl("null_seen_(DidNotAttend|Requested|Blocked|Waiting|CancelledbyPatient|CancelledbyUnit|CancelledbyOtherService|NoAccessVisit|CancelledDueToDeath)", measure) ~ "null_seen_Uncompleted",
      grepl("start_and_reasonable_seen_(Arrived|InProgress|Finished|Visit|PatientWalkedOut)", measure) ~ "start_and_reasonable_seen_Completed",
      grepl("seen_and_reasonable_start_(Arrived|InProgress|Finished|Visit|PatientWalkedOut)", measure) ~ "seen_and_reasonable_start_Completed",
      grepl("null_start_(Arrived|InProgress|Finished|Visit|PatientWalkedOut)", measure) ~ "null_start_Completed",
      grepl("null_seen_(Arrived|InProgress|Finished|Visit|PatientWalkedOut)", measure) ~ "null_seen_Completed",
      TRUE ~ measure
    )
  )

# Creating the dataframe for the lineplot that only contains start-seen-status combinations
start_seen_combos <- c("start_and_reasonable_seen_Uncompleted","seen_and_reasonable_start_Uncompleted",
"null_start_Uncompleted","null_seen_Uncompleted","start_and_reasonable_seen_Completed","seen_and_reasonable_start_Completed",
"null_start_Completed","null_seen_Completed")
start_seen_combos_df <- appointments %>%
  filter(category %in% start_seen_combos) %>%
  group_by(interval_start, category) %>%
  summarise(numerator = sum(numerator, na.rm = TRUE))  # Summing the numerator

# Create line plot for each of status for each start-seen-status combination
plot <- ggplot(start_seen_combos_df, aes(x=interval_start, y=numerator, group = category, color=category)) +
    geom_line()+
    geom_point()+
    labs(x='Interval start date', y='Count', title='Start and seen statuses')
ggsave(glue('output/appointments/start_seen_combos_frequencies.png'))