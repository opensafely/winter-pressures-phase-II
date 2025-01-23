# --- YAML HEADER ---

yaml_header = """
version: '3.0'

expectations:
  population_size: 1000

actions:
"""

# --- YAML MEASURES BODY ----
from datetime import datetime, timedelta

# Generate annual start days for the study period: August 2016 -  31 July 2024
start_date = datetime.strptime('2024-07-31', '%Y-%m-%d') - timedelta(weeks=52)

# Subtract 52 weeks until we reach August 2016
dates = []
current_date = start_date

# Loop to subtract 52 weeks (1 year) in each iteration
while current_date.year > 2016 or (current_date.year == 2016 and current_date.month > 7):
    dates.append(current_date.strftime('%Y-%m-%d'))
    current_date -= timedelta(weeks=52)

# Start with the earliest date
dates.reverse()

# Patient and practice measures flags to loop
flags = ["patient_measures", "practice_measures"]

# Temple for measures generation, for each combination of patient/practice measure and start_intv date
yaml_template = """
  generate_{flag}_{date}:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/{flag}/{flag}_{date}.csv.gz
      --
      --{flag}
      --start_intv {date}
    outputs:
      highly_sensitive:
        dataset: output/{flag}/{flag}_{date}.csv.gz
"""

yaml_body = ""
all_needs = []

for flag in flags:
    for date in dates:
        yaml_body += yaml_template.format(flag = flag, date = date)
        all_needs.append(f"generate_{flag}_{date}")

needs_list = ", ".join(all_needs)

# --- YAML APPT REPORT ---
yaml_appt_report = ""

appt_dates = {
    1: datetime.strptime("2023-07-01", "%Y-%m-%d").date(),
    2: datetime.strptime("2023-12-01", "%Y-%m-%d").date(),
    3: datetime.strptime("2018-07-01", "%Y-%m-%d").date(),
    4: datetime.strptime("2018-12-01", "%Y-%m-%d").date()
}

appt_needs = []

yaml_appt_template = """
  generate_app_measures_intv_{key}:
     run: ehrql:v1 generate-measures analysis/appointments/app_measures.py
      --output output/appointments/app_measures_{key}.csv 
      -- 
      --start_intv {appt_date}
     outputs:
       moderately_sensitive:
         dataset: output/appointments/app_measures_{key}.csv
 """ 

for key, value in appt_dates.items():
    yaml_appt_report += yaml_appt_template.format(key = key, appt_date = value)
    appt_needs.append(f"generate_app_measures_intv_{key}")

appt_list = ", ".join(appt_needs)

yaml_appt_processing_template = """
  generate_app_processing:
     run: r:latest analysis/appointments/app_processing.r
     needs: [{appt_list}]
     outputs:
       moderately_sensitive:
         table_rounded: output/appointments/app_measures_rounded_*.csv
         table_pivot: output/appointments/app_pivot_table_*.csv
"""
yaml_appt_processing = yaml_appt_processing_template.format(appt_list=appt_list)

yaml_appt_report = yaml_appt_report + yaml_appt_processing

# --- YAML FILE PROCESSING ---
yaml_processing = """
  generate_pre_processing:
    run: python:latest analysis/pre_processing.py 
        --output output/practice_measures/processed_practice_measures.csv.gz
        --output output/patient_measures/processed_patient_measures.csv.gz
        --output output/patient_measures/frequency_table.csv
    needs: [generate_patient_measures, generate_practice_measures]
    outputs:
      highly_sensitive:
        practice_measure: output/practice_measures/processed_practice_measures.csv.gz
        patient_measure: output/patient_measures/processed_patient_measures.csv.gz
      moderately_sensitive:
        frequency_table: output/patient_measures/frequency_table.csv
  generate_tables:
    run: r:latest analysis/table_generation.r
    needs: [generate_pre_processing]
    outputs:
      moderately_sensitive:
        total_measures: output/total_measures/*.csv
        practice_measures: output/practice_measures/*.csv
        patient_measures: output/patient_measures/*.csv
"""

# --- YAML TESTING ---
  # generate_test_data:
  #   run: ehrql:v1 generate-dataset analysis/dataset.py --output output/patient_measures/test.csv --test-data-file analysis/test_dataset.py
  #   outputs:
  #     highly_sensitive:
  #       dataset: output/patient_measures/test.csv


# --- Combine scripts and print file ---
yaml = yaml_header + yaml_body + yaml_appt_report

with open("project.yaml", "w") as file:
       file.write(yaml)