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
from wp_config_setup import *

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=1000)
measures.configure_disclosure_control(enabled=False)

# Date specifications
study_start_date = "2022-01-01"

# Exclusion criteria ---

# Age 0 - 110 (as per WP2)
age_at_interval_start = patients.age_on(INTERVAL.start_date)
age_filter = (age_at_interval_start >= 0) & (
    age_at_interval_start <= 110)

# Alive throughout the interval period (vs. at the beginning)
was_alive = (
    patients.date_of_death.is_after(INTERVAL.end_date) | 
    patients.date_of_death.is_null()
)

# Registered throughout the interval period and 90 days before
was_registered = practice_registrations.spanning((INTERVAL.start_date - days(90)), INTERVAL.end_date).exists_for_patient()

# No missing data: known sex, IMD, practice region (as per WP 2) 
was_female_or_male = patients.sex.is_in(["female", "male"])
has_deprivation_index = addresses.for_patient_on(INTERVAL.start_date).imd_rounded.is_not_null()
has_region = practice_registrations.for_patient_on(INTERVAL.start_date).practice_nuts1_region_name.is_not_null()

# Patient characteristics ---

# Age subgroups
age = age_at_interval_start
age_group = case(
    when((age >= 0) & (age < 5)).then("preschool"),
    when((age >= 5) & (age < 12)).then("primary_school"),
    when((age >= 12) & (age < 18)).then("secondary_school"),
    when((age >= 18) & (age < 40)).then("adult_under_40"),
    when((age >= 40) & (age < 65)).then("adult_under_65"),
    when((age >= 65) & (age < 80)).then("adult_under_80"),
    when((age >= 80) & (age < 111)).then("adult_over_80")
)

# Ethnicity
ethnicity = (
    clinical_events.where(clinical_events.ctv3_code.is_in(ethnicity))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .ctv3_code.to_category(ethnicity)
)

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

# Vaccination against flu or covid in the last 12 months
vax_status = {}
for disease in ['INFLUENZA', 'SARS-2 CORONAVIRUS', 'PNEUMOCOCCAL']:
    vax_status[disease] = (vaccinations.where((vaccinations
                                        .target_disease
                                        .is_in([disease])) &
                                        vaccinations
                                        .date
                                        .is_on_or_between(INTERVAL.start_date - years(1), INTERVAL.start_date))
                                        .exists_for_patient())

# Co-morbidity
# Check if patient had a resolvable condition in the interval
comorbid_copd = check_resolved_condition(comorbid_dict["copd"], comorbid_dict["copd_res"], INTERVAL.start_date)
comorbid_asthma = check_resolved_condition(comorbid_dict["asthma"], comorbid_dict["asthma_res"], INTERVAL.start_date)
comorbid_dm = check_resolved_condition(comorbid_dict["diabetes"], comorbid_dict["diabetes_res"], INTERVAL.start_date)
comorbid_htn = check_resolved_condition(comorbid_dict["htn"], comorbid_dict["htn_res"], INTERVAL.start_date)
comorbid_depres = check_resolved_condition(comorbid_dict["depres"], comorbid_dict["depres_res"], INTERVAL.start_date)

# Check if patient had an unresolvable (chronic) condition in the interval
comorbid_chronic_resp = check_chronic_condition(comorbid_dict["chronic_resp"], INTERVAL.start_date)
comorbid_mh = check_chronic_condition(comorbid_dict["mental_health"], INTERVAL.start_date)
comorbid_neuro = check_chronic_condition(comorbid_dict["neuro"], INTERVAL.start_date)
comorbid_immuno = check_chronic_condition(comorbid_dict["immuno_sup"], INTERVAL.start_date)

# Measures ---
measures_to_add = {}
# Valid appointments are those where seen_date is in interval
valid_appointments = create_valid_appointments()

# Number of appointments in interval
measures_to_add['appointments_in_interval'] = count_appointments_in_interval(INTERVAL.start_date, INTERVAL.end_date)

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
    # Number of follow-up appointments:
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

if patient_measures == True:
    # Run patient script if patient flag called
    measures.define_defaults(
        denominator= was_female_or_male & age_filter & was_alive & 
                    was_registered & has_deprivation_index & has_region,
        group_by={
            "age": age_group,
            "sex": patients.sex,
            "ethnicity": ethnicity,
            "imd_quintile": imd_quintile,
            "carehome": carehome,
            "region": region,
            "rur_urb_class": rur_urb_class,
            "comorbid_chronic_resp": comorbid_chronic_resp,
            "comorbid_copd": comorbid_copd,
            "comorbid_asthma": comorbid_asthma,
            "comorbid_dm": comorbid_dm,
            "comorbid_htn": comorbid_htn,
            "comorbid_depres": comorbid_depres,
            "comorbid_mh": comorbid_mh,
            "comorbid_neuro": comorbid_neuro,
            "comorbid_immuno": comorbid_immuno,
            "vax_flu_12m": vax_status['INFLUENZA'],
            "vax_covid_12m": vax_status['SARS-2 CORONAVIRUS'],
            "vax_pneum_12m": vax_status['PNEUMOCOCCAL']
        },
        intervals=weeks(2).starting_on(study_start_date),
    )

if practice_measures == True:
    # Run practice script if practice flag called
    measures.define_defaults(
        denominator= was_female_or_male & age_filter & was_alive & 
                    was_registered & has_deprivation_index & has_region,
        group_by={
            #"age": age_group,
            "sex": patients.sex,
            #"ethnicity": ethnicity,
            "imd_quintile": imd_quintile,
            "carehome": carehome,
            "region": region,
            "rur_urb_class": rur_urb_class,
            "practice_pseudo_id": practice_id
        },
        intervals=weeks(2).starting_on(study_start_date),
    )

# Adding measures
for measure in measures_to_add.keys():
    measures.define_measure(
        name=measure,
        numerator=measures_to_add[measure],
    )
