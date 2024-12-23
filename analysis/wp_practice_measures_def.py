from ehrql import case, codelist_from_csv, create_dataset, days, weeks, years, when, INTERVAL, create_measures
from ehrql.tables.core import medications, patients
from ehrql.tables.tpp import (
    addresses,
    opa_cost,
    clinical_events,
    practice_registrations,
    appointments,
    vaccinations
)
from queries import *
from codelist_definition import *

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=1000)
measures.configure_disclosure_control(enabled=False)

# Configuration
import argparse
parser = argparse.ArgumentParser() # Instantiate parser
parser.add_argument("--drop_follow_up", action = 'store_true', help = "Drops follow_up if flag is added to action, otherwise all measures included") # Add flags
parser.add_argument("--drop_indicat_prescript", action = 'store_true', help = "Drops indicat/prescript if flag is added to action, otherwise all measures included") 
parser.add_argument("--drop_prescriptions", action = 'store_true', help = "Drops prescriptions if flag is added to action, otherwise all measures included") 
parser.add_argument("--drop_reason", action = 'store_true', help = "Drops reason if flag is added to action, otherwise all measures included") 
args = parser.parse_args() # Stores arguments in 'args'
drop_follow_up = args.drop_follow_up # extracts arguments
drop_indicat_prescript = args.drop_indicat_prescript
drop_prescriptions = args.drop_prescriptions
drop_reason = args.drop_reason

# Date specifications
study_start_date = "2022-01-03"
study_reg_date = "2021-10-03"

# exclusion criteria ---

# Age 0 - 110 (as per WP2)
age_at_interval_start = patients.age_on(INTERVAL.start_date)
age_filter = (age_at_interval_start >= 0) & (
    age_at_interval_start <= 110)

# Alive throughout the interval period (vs. at the beginning)
was_alive = (
    patients.date_of_death.is_after(INTERVAL.end_date) | 
    patients.date_of_death.is_null()
)

# Registered throughout the interval period (vs at the begining)
was_registered = practice_registrations.spanning(INTERVAL.start_date, INTERVAL.end_date).exists_for_patient()
# Been registered at a practice for 90 days before the study
prior_registration = practice_registrations.spanning(study_reg_date, study_start_date).exists_for_patient()

# No missing data: known sex, IMD, practice region (as per WP 2) 
was_female_or_male = patients.sex.is_in(["female", "male"])
has_deprivation_index = addresses.for_patient_on(INTERVAL.start_date).imd_rounded.is_not_null()
has_region = practice_registrations.for_patient_on(INTERVAL.start_date).practice_nuts1_region_name.is_not_null()

# Patient characteristics ---

# Age subgroups
age = age_at_interval_start
age_group = case(
    when((age >= 0) & (age < 5)).then("preschool"),
    when((age >= 5) & (age < 12)).then("primary-school"),
    when((age >= 12) & (age < 18)).then("secondary-school"),
    when((age >= 18) & (age < 40)).then("adult-under40"),
    when((age >= 40) & (age < 65)).then("adult-under65"),
    when((age >= 65) & (age < 80)).then("adult-under80"),
    when((age >= 80) & (age < 111)).then("adult-80plus")
)

# Ethnicity
# ethnicity = (
#    clinical_events.where(clinical_events.ctv3_code.is_in(ethnicity))
#    .sort_by(clinical_events.date)
#    .last_for_patient()
#    .ctv3_code.to_category(ethnicity)
#)

# Depravation
imd_rounded = addresses.for_patient_on(INTERVAL.start_date).imd_rounded
max_imd = 32844
imd_quintile = case(
    when(imd_rounded < int(max_imd * 1 / 5)).then(1),
    when(imd_rounded < int(max_imd * 2 / 5)).then(2),
    when(imd_rounded < int(max_imd * 3 / 5)).then(3),
    when(imd_rounded < int(max_imd * 4 / 5)).then(4),
    when(imd_rounded <= max_imd).then(5),
)

# Care home residency
carehome = addresses.for_patient_on(INTERVAL.start_date).care_home_is_potential_match

# Defining interval events for reusability in later queries
interval_events = clinical_events.where(clinical_events
                                        .date.is_during(INTERVAL))

# Patient urban-rural classification
rur_urb_class = (addresses
                 .for_patient_on(INTERVAL.start_date)
                 .rural_urban_classification)

# Practice data taken at the start of the interval
practice_id = (practice_registrations.for_patient_on(INTERVAL.start_date)
               .practice_pseudo_id)
region = (practice_registrations.for_patient_on(INTERVAL.start_date)
          .practice_nuts1_region_name)

# Measures ---
measures_to_add = {}
# Valid appointments are those where start_date == seen_date
# because incomplete appointments may have been coded with extreme dates (e.g. 9999)
valid_appointments = create_valid_appointments()

# Number of appointments in interval
measures_to_add['appointments_in_interval'] = count_appointments_in_interval(INTERVAL.start_date, INTERVAL.end_date, valid_appointments, valid_only=True)
measures_to_add['all_appointments_in_interval'] = count_appointments_in_interval(INTERVAL.start_date, INTERVAL.end_date, valid_appointments, valid_only=False)

# Number of vaccinations during interval, all and for flu and covid
measures_to_add['vax_app'] = count_vaccinations(INTERVAL.start_date, INTERVAL.end_date)
measures_to_add['vax_app_flu'] = count_vaccinations(INTERVAL.start_date, INTERVAL.end_date, ['INFLUENZA'])
measures_to_add['vax_app_covid'] = count_vaccinations(INTERVAL.start_date, INTERVAL.end_date, ['SARS-2 CORONAVIRUS'])

# Number of secondary care referrals during intervals
# Note that opa table is unsuitable for regional comparisons and 
# doesn't include mental health care and community services
measures_to_add['secondary_referral'] = count_secondary_referral(INTERVAL.start_date, INTERVAL.end_date)

# Count number of appointments with cancelled/waiting status during interval
app_status_code = ['Cancelled by Unit','Waiting']
app_status_measure = ['cancelled_app', 'waiting_app']
for status_code, status_measure in zip(app_status_code, app_status_measure):
    measures_to_add[status_measure] = count_appointments_by_status(INTERVAL.start_date, INTERVAL.end_date, status_code)

# Configuration based on CLI arg. Skip these measures if --drop_measures flag was called in action
if drop_follow_up == False:
    # Count number of follow-up appointments:
    measures_to_add["follow_up_app"] = count_follow_up(INTERVAL.start_date, INTERVAL.end_date)

if drop_indicat_prescript == False:

    # Count appointments with an indication and prescription
    measures_to_add.update(appointments_with_indication_and_prescription(INTERVAL.start_date, INTERVAL.end_date, indication_dict, prescription_dict, valid_appointments))


if drop_prescriptions == False:

    # Count prescriptions and add to measures
    measures_to_add.update(count_prescriptions(INTERVAL.start_date, INTERVAL.end_date, med_dict))


if drop_reason == False:

    # Adding reason for appointment (inferred from appointment and reason being on the same day)
    for reason in app_reason_dict.keys():
        measures_to_add[reason] = count_reason_for_app(INTERVAL.start_date, INTERVAL.end_date, app_reason_dict[reason], valid_appointments)


# Defining measures ---
measures.define_defaults(
    denominator= was_female_or_male & age_filter & was_alive & 
                was_registered & has_deprivation_index & has_region & 
                prior_registration,
    group_by={
        "age": age_group,
        "sex": patients.sex,
        #"ethnicity": ethnicity,
        "imd_quintile": imd_quintile,
        "carehome": carehome,
        "region": region,
        "rur_urb_class": rur_urb_class,
        "practice_pseudo_id": practice_id
    },
    intervals=weeks(1).starting_on(study_start_date),
)

# Adding measures
for measure in measures_to_add.keys():
    measures.define_measure(
        name=measure,
        numerator=measures_to_add[measure],
    )
