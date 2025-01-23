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
start_date = datetime.strptime('31-07-2024', '%d-%m-%Y')

# Subtract 52 weeks until we reach August 2016
dates = []
current_date = start_date

# Loop to subtract 52 weeks (1 year) in each iteration
while current_date.year > 2016 or (current_date.year == 2016 and current_date.month > 7):
    dates.append(current_date.strftime('%d-%m-%Y'))
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
      --start_intv "{date}"
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
yaml_appt_report = """
  generate_app_measures_intv_1:
     run: ehrql:v1 generate-measures --output output/appointments/app_measures_1.csv analysis/appointments/app_measures.py -- --start_intv 2023-07-01
     outputs:
       moderately_sensitive:
         dataset: output/appointments/app_measures_1.csv
  generate_app_measures_intv_2:
     run: ehrql:v1 generate-measures --output output/appointments/app_measures_2.csv analysis/appointments/app_measures.py -- --start_intv 2023-12-01
     outputs:
       moderately_sensitive:
         dataset: output/appointments/app_measures_2.csv
  generate_app_measures_intv_3:
    run: ehrql:v1 generate-measures --output output/appointments/app_measures_3.csv analysis/appointments/app_measures.py -- --start_intv 2018-07-01
    outputs:
      moderately_sensitive:
        dataset: output/appointments/app_measures_3.csv
  generate_app_measures_intv_4:
    run: ehrql:v1 generate-measures --output output/appointments/app_measures_4.csv analysis/appointments/app_measures.py -- --start_intv 2018-12-01
    outputs:
      moderately_sensitive:
        dataset: output/appointments/app_measures_4.csv
"""

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
print(yaml)
# Save to a file
# with open("project.yaml", "w") as file:
#     file.write(yamll)