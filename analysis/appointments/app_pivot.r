# TODO:
# Extract ratios to comapare between intervals

library(tidyverse)
library(glue)

statuses <- c('Booked', 'Arrived', 'DidNotAttend', 'InProgress', 'Finished',
              'Requested', 'Blocked', 'Visit', 'Waiting', 'CancelledbyPatient',
              'CancelledbyUnit', 'CancelledbyOtherService', 'NoAccessVisit',
              'CancelledDueToDeath', 'PatientWalkedOut')


df_1 <- read.csv("output/appointments/app_measures_rounded_1.csv")
df_2 <- read.csv("output/appointments/app_measures_rounded_2.csv")
df_3 <- read.csv("output/appointments/app_measures_rounded_3.csv")
df_4 <- read.csv("output/appointments/app_measures_rounded_4.csv")

df_combined <- rbind(df_1, df_2, df_3, df_4)
write_csv(df_combined, "output/appointments/app_measures_combined.csv")

# Split by status
df_pivot <- df_combined %>%
    mutate(
        status = str_extract(measure, paste(statuses, collapse = "|")),
        measure = str_remove(measure, paste(status, collapse = "|"))
        ) %>%
    mutate(
        measure = str_remove(measure, "_$")
        )

df_pivot <- df_pivot %>%
select(- c(interval_end, ratio))

df_pivot <- df_pivot %>%
    rename(
        numerator = midpoint_rounded_numerator,
        denominator = midpoint_rounded_denominator) %>%
            pivot_wider(names_from = status, values_from = numerator)

write_csv(df_pivot,"output/appointments/app_pivot_table.csv")
