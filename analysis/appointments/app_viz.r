library(ggplot2)
library(dplyr)
library(glue)

# Import appointments data
appointments <- read.csv('output/appointments/app.csv')
appointments$interval_start <- as.Date(appointments$interval_start)
appointments$interval_end <- as.Date(appointments$interval_end)

# Create plots for each set of appointments
for (app_type in unique(appointments$measure)){
    df <- filter(appointments,measure==app_type)
    plot <- ggplot(df, aes(x=interval_start, y=numerator)) +
        geom_line()+
        geom_point()+
        labs(x='Interval start date', y='Count', title=glue('{app_type} over time'))
    ggsave(glue('output/appointments/{app_type}_frequencies.png'))
}