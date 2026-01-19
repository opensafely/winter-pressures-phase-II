# This script creates a dataset definition copy of the measures definition for testing purposes

from ehrql import (
    case,
    codelist_from_csv,
    create_dataset,
    days,
    weeks,
    years,
    when,
    INTERVAL,
    create_measures,
)
from ehrql.tables.core import medications, patients
from ehrql.tables.tpp import (
    addresses,
    opa_cost,
    clinical_events,
    practice_registrations,
    appointments,
    vaccinations,
    emergency_care_attendances,
)

from queries import *
from codelist_definition import *
from ehrql import claim_permissions

claim_permissions("appointments")
# Instantiate measures, with small number suppression turned off
dataset = create_dataset()

# Date specifications
study_start_date = "2022-01-14"
study_reg_date = "2021-01-14"
study_end_date = "2022-01-21"

# exclusion criteria ---

# Age 0 - 110 (as per WP2)
age_at_interval_start = patients.age_on(study_start_date)
age_filter = (age_at_interval_start >= 0) & (age_at_interval_start <= 110)

# Alive throughout the interval period (vs. at the beginning)
was_alive = (
    patients.date_of_death.is_after(study_end_date) | patients.date_of_death.is_null()
)

# Registered throughout the interval period (vs at the begining)
was_registered = practice_registrations.spanning(
    study_start_date, study_end_date
).exists_for_patient()
# Been registered at a practice for 365 days before the study
prior_registration = practice_registrations.spanning(
    study_reg_date, study_start_date
).exists_for_patient()

# No missing data: known sex, IMD, practice region (as per WP 2)
was_female_or_male = patients.sex.is_in(["female", "male"])
has_deprivation_index = addresses.for_patient_on(
    study_start_date
).imd_rounded.is_not_null()
has_region = practice_registrations.for_patient_on(
    study_start_date
).practice_nuts1_region_name.is_not_null()

# Patient characteristics ---

# Age subgroups
age = age_at_interval_start
age_group = case(
    when((age >= 0) & (age < 5)).then("preschool"),
    when((age >= 5) & (age < 12)).then("primary-school"),
    when((age >= 12) & (age < 18)).then("secondary-school"),
    when((age >= 18) & (age < 40)).then("adult<40"),
    when((age >= 40) & (age < 65)).then("adult<65"),
    when((age >= 65) & (age < 80)).then("adult<80"),
    when((age >= 80) & (age < 111)).then("adult>80"),
)

# Ethnicity
dataset.ethnicity = (
    clinical_events.where(clinical_events.snomedct_code.is_in(ethnicity))
    .where(clinical_events.date.is_on_or_before(study_start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .snomedct_code.to_category(ethnicity)
)

# Depravation
imd_rounded = addresses.for_patient_on(study_start_date).imd_rounded
max_imd = 32844
imd_quintile = case(
    when((imd_rounded >= 0) & (imd_rounded <= int(max_imd * 1 / 5))).then(1),
    when(imd_rounded <= int(max_imd * 2 / 5)).then(2),
    when(imd_rounded <= int(max_imd * 3 / 5)).then(3),
    when(imd_rounded <= int(max_imd * 4 / 5)).then(4),
    when(imd_rounded <= max_imd).then(5),
    otherwise=99,
)

# Care home residency
dataset.carehome = addresses.for_patient_on(
    study_start_date
).care_home_is_potential_match

# Defining interval events for reusability in later queries
interval_events = clinical_events.where(
    clinical_events.date.is_on_or_between(study_start_date, study_end_date)
)

# Patient urban-rural classification
dataset.rur_urb_class = addresses.for_patient_on(
    study_start_date
).rural_urban_classification

# Practice data taken at the start of the interval
dataset.practice_id = practice_registrations.for_patient_on(
    study_start_date
).practice_pseudo_id
dataset.region = practice_registrations.for_patient_on(
    study_start_date
).practice_nuts1_region_name

# Vaccination against flu or covid in the last 12 months
vax_status = {}
for disease in ["INFLUENZA", "SARS-2 CORONAVIRUS", "PNEUMOCOCCAL"]:
    vax_status[disease] = vaccinations.where(
        (vaccinations.target_disease.is_in([disease]))
        & vaccinations.date.is_on_or_between(
            study_start_date - years(1), study_start_date
        )
    ).exists_for_patient()

# Co-morbidity
# Check if patient had a resolvable condition in the interval
dataset.comorbid_copd = check_resolved_condition(
    comorbid_dict["copd"], comorbid_dict["copd_res"], study_start_date
)
dataset.comorbid_asthma = check_resolved_condition(
    comorbid_dict["asthma"], comorbid_dict["asthma_res"], study_start_date
)
dataset.comorbid_dm = check_resolved_condition(
    comorbid_dict["diabetes"], comorbid_dict["diabetes_res"], study_start_date
)
dataset.comorbid_htn = check_resolved_condition(
    comorbid_dict["htn"], comorbid_dict["htn_res"], study_start_date
)

# Check if patient had an unresolvable (chronic) condition in the interval
dataset.comorbid_chronic_resp = check_chronic_condition(
    comorbid_dict["chronic_resp"], study_start_date
)
dataset.comorbid_immuno = check_chronic_condition(
    comorbid_dict["immuno_sup"], study_start_date
)

# Measures ---
measures_to_add = {}
# Valid appointments are those where start_date == seen_date
# because incomplete appointments may have been coded with extreme dates (e.g. 9999)
seen_appts_in_interval = create_seen_appts_in_interval(study_start_date, study_end_date)

# Number of appointments in interval
dataset.seen_in_interval = count_seen_in_interval(seen_appts_in_interval)
dataset.start_in_interval = count_start_in_interval(study_start_date, study_end_date)

# Count number of consultations in interval
dataset.online_consult = count_clinical_consultations(
    online_consult, "many_pp", study_start_date, study_end_date
)
dataset.call_from_patient = count_clinical_consultations(
    "25691000000103", "many_pp", study_start_date, study_end_date
)
dataset.call_from_gp = count_clinical_consultations(
    "24671000000101", "many_pp", study_start_date, study_end_date
)
dataset.tele_consult = count_clinical_consultations(
    "386472008", "many_pp", study_start_date, study_end_date
)
dataset.emergency_care = count_emergency_care_attendance(
    study_start_date, study_end_date
)

# Number of follow-up appointments:
dataset.follow_up_app = count_follow_up(study_start_date, seen_appts_in_interval)

# Number of vaccinations during interval, all and for flu and covid
dataset.vax_app = count_vaccinations(study_start_date, study_end_date)
dataset.vax_app_flu = count_vaccinations(
    study_start_date, study_end_date, ["INFLUENZA"]
)
dataset.vax_app_covid = count_vaccinations(
    study_start_date, study_end_date, ["SARS-2 CORONAVIRUS"]
)

# Count sro measures in interval
for key in sro_dict.keys():
    result = count_clinical_consultations(
        sro_dict[key], "many_pp", study_start_date, study_end_date
    )
    dataset.add_column(key, result)

# Combine prioritized and deprioritized sro measures (match wp_measures behaviour)
prioritized_sum = sum(
    [
        count_clinical_consultations(
            sro_dict[sro], "many_pp", study_start_date, study_end_date
        )
        for sro in config["prioritized"]
    ]
)
deprioritized_sum = sum(
    [
        count_clinical_consultations(
            sro_dict[sro], "many_pp", study_start_date, study_end_date
        )
        for sro in config["deprioritized"]
    ]
)

dataset.add_column("sro_prioritized", prioritized_sum)
dataset.add_column("sro_deprioritized", deprioritized_sum)

# Count sro measures with appt in interval (appt_<measure>) to match wp_measures
for key in sro_dict.keys():
    appt_series = restrict_to_seen_appts(
        count_clinical_consultations(
            sro_dict[key], "many_pp", study_start_date, study_end_date
        ),
        seen_appts_in_interval,
    )
    dataset.add_column(f"appt_{key}", appt_series)

dataset.add_column(
    "appt_sro_prioritized",
    restrict_to_seen_appts(prioritized_sum, seen_appts_in_interval),
)
dataset.add_column(
    "appt_sro_deprioritized",
    restrict_to_seen_appts(deprioritized_sum, seen_appts_in_interval),
)

# ---- SPECIFIC AND SENSITIVE SEASONAL ILLNESSES ------------------

dataset.flu_sensitive = count_seasonal_illness_sensitive(
    study_start_date,
    study_end_date,
    "flu",
    resp_dict["flu_sensitive"],
    flu_med_codelist,
    flu_sensitive_exclusion,
    resp_dict["flu_specific"],
)

dataset.rsv_sensitive = count_seasonal_illness_sensitive(
    study_start_date,
    study_end_date,
    "rsv",
    resp_dict["rsv_sensitive"],
    rsv_med_codelist,
    rsv_sensitive_exclusion,
    resp_dict["rsv_specific"],
)

dataset.covid_sensitive = count_seasonal_illness_sensitive(
    study_start_date,
    study_end_date,
    "covid",
    resp_dict["covid_sensitive"],
    covid_med_codelist,
    covid_sensitive_exclusion,
    resp_dict["covid_specific"],
)

dataset.ili = count_seasonal_illness_sensitive(
    study_start_date,
    study_end_date,
    "ili",
    resp_dict[
        "flu_sensitive"
    ],  # these arguments and below not actually used in ili measure
    flu_med_codelist,
    flu_sensitive_exclusion,
    resp_dict["flu_specific"],
)

dataset.overall_resp_sensitive = count_mild_overall_resp_illness(
    study_start_date,
    study_end_date,
    dataset.flu_sensitive,
    dataset.covid_sensitive,
    dataset.rsv_sensitive,
    age,
)

# Max specificity

for codelist in resp_dict.keys():
    if "specific" in codelist:
        counts = count_clinical_consultations(
            resp_dict[codelist], "one_pp", study_start_date, study_end_date
        )
        dataset.add_column(codelist, counts)

# Limit to cases with appt in the same interval to reduce secondary discharge codes
resp_measures = ["overall_resp_sensitive"]
diseases = ["flu", "rsv", "covid"]
sensitivities = ["specific", "sensitive"]
for illness in diseases:
    for sensitivity in sensitivities:
        resp_measures.append(f"{illness}_{sensitivity}")

# Dynamically reference each respiratory measure and create appt_ variant
for resp_measure in resp_measures:
    measure = getattr(dataset, resp_measure)
    dataset.add_column(
        f"appt_{resp_measure}", restrict_to_seen_appts(measure, seen_appts_in_interval)
    )

# Count number of appts for sick notes
dataset.sick_notes = count_clinical_consultations(
    app_reason_dict["sick_notes"],
    "many_pp",
    study_start_date,
    study_end_date,
)
dataset.add_column(
    "appt_sick_notes",
    restrict_to_seen_appts(dataset.sick_notes, seen_appts_in_interval),
)

# Number of secondary care referrals during intervals
# Note that opa table is unsuitable for regional comparisons and
# doesn't include mental health care and community services
dataset.secondary_referral = count_secondary_referral(
    study_start_date, study_end_date, type="referral_date"
)
dataset.secondary_appt = count_secondary_referral(
    study_start_date, study_end_date, type="appointment_date"
)

# Count number of appointments with cancelled/waiting status during interval
app_status_code = ["Cancelled by Unit", "Waiting"]
app_status_measure = ["cancelled_app", "waiting_app"]
for status_code, status_measure in zip(app_status_code, app_status_measure):
    status_count = count_appointments_by_status(
        study_start_date, study_end_date, status_code
    )
    dataset.add_column(status_measure, status_count)

# Count prescriptions
prescription_counts = count_prescriptions(study_start_date, study_end_date, med_dict)
for prescription in prescription_counts.keys():
    dataset.add_column(prescription, prescription_counts[prescription])

# Count prescriptions for each indication
indication_counts = appointments_with_indication_and_prescription(
    study_start_date,
    study_end_date,
    indication_dict,
    prescription_dict,
    seen_appts_in_interval,
)
for indication in indication_counts.keys():
    dataset.add_column(indication, indication_counts[indication])

dataset.define_population(
    was_female_or_male
    & age_filter
    & was_alive
    & was_registered
    & has_deprivation_index
    & has_region
    & prior_registration
)
