from datetime import datetime, timedelta

def generate_annual_dates(start_year, end_date):
    """
    Generates a list of annual start dates from the start year to the end date.
    
    Args:
        start_year: The starting year for the dates.
        end_date: The end date for the dates.
        
    Returns:
        A list of annual start dates in 'YYYY-MM-DD' format.
    """
    # Generate annual start days for the study period: August 2016 -  31 July 2024
    start_date = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(weeks=52)

    # Subtract 52 weeks until we reach August 2016
    dates = []
    current_date = start_date

    # Loop to subtract 52 weeks (1 year) in each iteration
    while current_date.year > start_year or (current_date.year == start_year and current_date.month > 7):
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date -= timedelta(weeks=52)

    dates.reverse()
    return dates