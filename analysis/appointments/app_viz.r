library(ggplot2)
library(dplyr)
library(glue)

# Import appointments data
appointments <- read.csv('output/appointments/app_measures.csv.gz')
appointments$interval_start <- as.Date(appointments$interval_start)
appointments$interval_end <- as.Date(appointments$interval_end)

# Grouping into larger categories using mutate and case_when
appointments <- appointments %>%
  mutate(
    category = case_when(
      grepl(paste0("start_and_reasonable_seen_DidNotAttend|start_and_reasonable_seen_Requested|",
      "start_and_reasonable_seen_Blocked|start_and_reasonable_seen_Waiting|start_and_reasonable_seen_CancelledbyPatient|",
      "start_and_reasonable_seen_CancelledbyUnit|start_and_reasonable_seen_CancelledbyOtherService|start_and_reasonable_seen_NoAccessVisit|",
      "start_and_reasonable_seen_CancelledDueToDeath"), measure) ~ "start_and_reasonable_seen_Uncompleted",
      grepl(paste0("seen_and_reasonable_start_DidNotAttend|seen_and_reasonable_start_Requested|",
      "seen_and_reasonable_start_Blocked|seen_and_reasonable_start_Waiting|seen_and_reasonable_start_CancelledbyPatient|",
      "seen_and_reasonable_start_CancelledbyUnit|seen_and_reasonable_start_CancelledbyOtherService|seen_and_reasonable_start_NoAccessVisit|",
      "seen_and_reasonable_start_CancelledDueToDeath"), measure) ~ "seen_and_reasonable_start_Uncompleted",
      grepl(paste0("proxy_null_start_DidNotAttend|proxy_null_start_Requested|",
      "proxy_null_start_Blocked|proxy_null_start_Waiting|proxy_null_start_CancelledbyPatient|",
      "proxy_null_start_CancelledbyUnit|proxy_null_start_CancelledbyOtherService|proxy_null_start_NoAccessVisit|",
      "proxy_null_start_CancelledDueToDeath"), measure) ~ "proxy_null_start_Uncompleted",
      grepl(paste0("proxy_null_seen_DidNotAttend|proxy_null_seen_Requested|",
      "proxy_null_seen_Blocked|proxy_null_seen_Waiting|proxy_null_seen_CancelledbyPatient|",
      "proxy_null_seen_CancelledbyUnit|proxy_null_seen_CancelledbyOtherService|proxy_null_seen_NoAccessVisit|",
      "proxy_null_seen_CancelledDueToDeath"), measure) ~ "proxy_null_seen_Uncompleted",
      grepl("start_and_reasonable_seen_Arrived|start_and_reasonable_seen_InProgress|start_and_reasonable_seen_Finished|start_and_reasonable_seen_Visit|start_and_reasonable_seen_PatientWalkedOut", measure) ~ "start_and_reasonable_seen_Completed",
      grepl("seen_and_reasonable_start_Arrived|seen_and_reasonable_start_InProgress|seen_and_reasonable_start_Finished|seen_and_reasonable_start_Visit|seen_and_reasonable_start_PatientWalkedOut", measure) ~ "seen_and_reasonable_start_Completed",
      grepl("proxy_null_start_Arrived|proxy_null_start_InProgress|proxy_null_start_Finished|proxy_null_start_Visit|proxy_null_start_PatientWalkedOut", measure) ~ "proxy_null_start_Completed",
      grepl("proxy_null_seen_Arrived|proxy_null_seen_InProgress|proxy_null_seen_Finished|proxy_null_seen_Visit|proxy_null_seen_PatientWalkedOut", measure) ~ "proxy_null_seen_Completed",
      TRUE ~ measure
    )
  )

start_seen_combos <- c("start_and_reasonable_seen_Uncompleted","seen_and_reasonable_start_Uncompleted",
"proxy_null_start_Uncompleted","proxy_null_seen_Uncompleted","start_and_reasonable_seen_Completed","seen_and_reasonable_start_Completed",
"proxy_null_start_Completed","proxy_null_seen_Completed")
start_seen_combos_df <- appointments %>%
  filter(category %in% start_seen_combos) %>%
  group_by(interval_start, category) %>%
  summarise(numerator = sum(numerator, na.rm = TRUE))  # Summing the numerator
  
# Create line plot for each of status for each start/seen combination
plot <- ggplot(start_seen_combos_df, aes(x=interval_start, y=numerator, group = category, color=category)) +
    geom_line()+
    geom_point()+
    labs(x='Interval start date', y='Count', title='Start and seen statuses')
ggsave(glue('output/appointments/start_seen_combos_frequencies.png'))