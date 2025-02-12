# Description:
# This script reads in the four csv files containing the rounded midpoint values for the appointment measures, 
# combines them into a single dataframe, and then pivots the data so that the numerator or ratios values are in columns by status. 

# Outputs:
# - app_measures_combined.csv: Combined dataframe of the four rounded midpoint csv files
# - app_pivot_counts.csv: Pivot table of the counts of numerator values by status
# - app_pivot_ratios.csv: Pivot table of the ratios of ratio values by status

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

# Select counts
df_pivot_counts <- df_pivot %>%
    select(- c(interval_end, ratio)) %>%
        rename(
            numerator = midpoint_rounded_numerator,
            denominator = midpoint_rounded_denominator,) %>%
                pivot_wider(names_from = status, values_from = numerator) %>%
                    rename(Total = "NA")

# Select ratios and round to 5 decimal places
df_pivot_ratios <- df_pivot %>%
    select(- c(interval_end, midpoint_rounded_numerator, midpoint_rounded_denominator)) %>%
        pivot_wider(names_from = status, values_from = ratio) %>%
            mutate(across(-c(measure, interval_start), round, 5)) %>%
                rename(Total = "NA")

write_csv(df_pivot_counts,"output/appointments/app_pivot_counts.csv")
write_csv(df_pivot_ratios,"output/appointments/app_pivot_ratios.csv")
