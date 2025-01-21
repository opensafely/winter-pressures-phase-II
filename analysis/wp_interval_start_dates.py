from datetime import datetime, timedelta

# Generate annual start days for the study period: August 2016 -  end July 2024

start_date = datetime.strptime('31-07-2024', '%d-%m-%Y')

# Subtract 52 weeks until we reach August 2016
dates = []
current_date = start_date

# Loop to subtract 52 weeks (1 year) in each iteration
while current_date.year > 2016 or (current_date.year == 2016 and current_date.month > 7):
    dates.append(current_date.strftime('%d-%m-%Y'))
    current_date -= timedelta(weeks=52)

print(dates)