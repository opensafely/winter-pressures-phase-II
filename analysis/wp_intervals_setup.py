from datetime import datetime, timedelta

# Define the start and end dates
start_date = datetime(2015, 1, 1)
end_date = datetime(2025, 1, 1)

# Initialize empty lists to store start and end dates
start_dates = []
end_dates = []

# Loop through every 6-month interval
current_date = start_date
while current_date < end_date:
    # Define the end of the current interval (6 months later)
    next_date = current_date + timedelta(days=183)  # 183 days approx for 6 months
    
    # Ensure the next interval doesn't go beyond the end_date
    if next_date > end_date:
        next_date = end_date

    # Format the dates as 'dd-mm-yyyy'
    interval_start = current_date.strftime('%d-%m-%Y')
    interval_end = next_date.strftime('%d-%m-%Y')

    # Append to the lists
    start_dates.append(interval_start)
    end_dates.append(interval_end)

    # Move to the next interval
    current_date = next_date + timedelta(days=1)

# Create a dictionary from the two lists, keys are start_dates, values are end_dates
intervals = dict(zip(start_dates, end_dates))
