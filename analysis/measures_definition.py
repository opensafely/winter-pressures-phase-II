# Task one: generate weekly appointment rates for elegible patients
# Task two: stratify by selected patient characteristics: age, sex, ethnicity, imd, care home residency, vaccination status & co-morbdiity

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

def create_codelist_dict(dic: dict) -> dict:
    '''
    Create a dicionary of codelists, so that queries can be run iteratively on
    codelists where appropriate
    '''
    for name in dic:
        dic[name] = codelist_from_csv(dic[name], 
                                                column = "code")
    return dic

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=1000)
measures.configure_disclosure_control(enabled=False)

# Date specifications
study_start_date = "2022-01-03"
study_reg_date = "2021-01-03"

# Demogragic codelists
ethnicity = codelist_from_csv(
    "codelists/opensafely-ethnicity.csv",
    column="Code",
    category_column="Grouping_6",
)

# Appointment reasons codelist:
app_reason_dict = {
    "flu_app": "codelists/opensafely-acute-respiratory-illness-primary-care.csv",
    "neurological_app": "codelists/ons-neurological-disorders.csv",
    "sick_notes_app": "codelists/opensafely-sick-notes-snomed.csv"
}
app_reason_dict = create_codelist_dict(app_reason_dict)

# Medications codelists:
med_dict ={
    "antidepressant_pres":"codelists/bristol-antidepressants-snomedct.csv",
    "antibiotic_pres":"codelists/opensafely-antibacterials.csv",
    "analgesic_nasal":"codelists/opensafely-opioid-containing-medicines-buccal-nasal-and-oromucosal-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_inhale":"codelists/opensafely-opioid-containing-medicines-inhalation-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_oral":"codelists/opensafely-opioid-containing-medicines-oral-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_parental":"codelists/opensafely-opioid-containing-medicines-parenteral-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_rectal":"codelists/opensafely-opioid-containing-medicines-rectal-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_transdermal":"codelists/opensafely-opioid-containing-medicines-transdermal-excluding-drugs-for-substance-misuse-dmd.csv",
}
med_dict = create_codelist_dict(med_dict)

# Co-morbidity codelists:
comorbid_dict = {
    "chronic_resp": "codelists/nhsd-primary-care-domain-refsets-crdatrisk1_cod.csv",
    "copd": "codelists/nhsd-primary-care-domain-refsets-copd_cod.csv",
    "copd_res": "codelists/nhsd-primary-care-domain-refsets-copdres_cod.csv",
    "asthma": "codelists/nhsd-primary-care-domain-refsets-ast_cod.csv",
    "asthma_res": "codelists/nhsd-primary-care-domain-refsets-astres_cod.csv",
    "diabetes": "codelists/nhsd-primary-care-domain-refsets-dm_cod.csv",
    "diabetes_res": "codelists/nhsd-primary-care-domain-refsets-dmres_cod.csv",
    "htn": "codelists/nhsd-primary-care-domain-refsets-hyp_cod.csv",
    "htn_res": "codelists/nhsd-primary-care-domain-refsets-hypres_cod.csv",
    "depres": "codelists/nhsd-primary-care-domain-refsets-depr_cod.csv",
    "depres_res": "codelists/nhsd-primary-care-domain-refsets-depres_cod.csv",
    "mental_health": "codelists/qcovid-has_severe_mental_illness.csv",
    "neuro": "codelists/primis-covid19-vacc-uptake-cns_cov.csv"
}
comorbid_dict = create_codelist_dict(comorbid_dict)

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
# Been registered at a practice for 365 days before the study
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
    when((age >= 5) & (age <18)).then("school"),
    when((age >= 18) & (age < 65)).then("adult"),
    when((age >= 65) & (age < 80)).then("retired"),
    when((age >= 80) & (age < 111)).then("elderly"),
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
for disease in ['influenza', 'covid']:
    vax_status[disease] = (vaccinations.where((vaccinations
                                        .target_disease
                                        .is_in([disease])) &
                                        vaccinations
                                        .date
                                        .is_on_or_between(INTERVAL.start_date - years(1), INTERVAL.start_date))
                                        .exists_for_patient())

# Co-morbidity

# Chronic resp disease (no resolution codelist). True if disease developed before interval start, else False.
comorbid_chronic_resp = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["chronic_resp"]))
    .sort_by(clinical_events.date)
    .first_for_patient()
    .date
    .is_on_or_before(INTERVAL.start_date)
    .when_null_then(False)
)

# COPD (with resolution codelist)
comorbid_copd_date_first = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["copd"]))
    .sort_by(clinical_events.date)
    .first_for_patient()
    .date
    .is_on_or_before(INTERVAL.start_date)
    .when_null_then(False)
)

comorbid_copd_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["copd"]))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

comorbid_copd_res_date = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["copd_res"]))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

comorbid_copd = comorbid_copd_date_first & (
    comorbid_copd_res_date.is_null() | (
        (comorbid_copd_res_date < comorbid_copd_date_last) & (comorbid_copd_date_last < (INTERVAL.start_date))
        )
        ) 

# Asthma (with resolution codelist)
comorbid_asthma_date_first = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["asthma"]))
    .sort_by(clinical_events.date)
    .first_for_patient()
    .date
)

comorbid_asthma_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["asthma"]))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

comorbid_asthma_res_date = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["asthma_res"]))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

# True if asthma developed before interval start & never resolved OR resolved but recurred before the interval; else False
comorbid_asthma = (
    (comorbid_asthma_date_first <= (INTERVAL.start_date)) & 
    (comorbid_asthma_res_date.is_null() | 
    ((comorbid_asthma_res_date < comorbid_asthma_date_last) & (comorbid_asthma_date_last < (INTERVAL.start_date)))
    )
).when_null_then(False)

# Chronic mental health disease (no resolution codelist). True if disease developed before interval start; else False
comorbid_mental_health = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["mental_health"]))
    .sort_by(clinical_events.date)
    .first_for_patient()
    .date
    .is_on_or_before(INTERVAL.start_date)
    .when_null_then(False)
)

# Chronic neurological disease (no resolution codelist). True if disease developed before interval start; else False
comorbid_neuro = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["neuro"]))
    .sort_by(clinical_events.date)
    .first_for_patient()
    .date
    .is_on_or_before(INTERVAL.start_date)
    .when_null_then(False)
)

# Measures ---
measures_to_add = {}
# Valid appointments are those where start_date == seen_date
# because incomplete appointments may have been coded with extreme dates (e.g. 9999)
valid_appointments = (appointments.where((appointments
                                            .start_date) ==
                                            (appointments
                                             .seen_date)))
# Number of appointments in interval
measures_to_add['appointments_in_interval'] = (valid_appointments.start_date
                            .is_during(INTERVAL)
                            .count_distinct_for_patient())
# Number of follow-up appointments, defined for a patient as
# the (number of appointments for the patient in a 2 week interval) - 1
measures_to_add["follow_up_app"] = (valid_appointments.start_date
                .is_on_or_between(INTERVAL.start_date - days(7), INTERVAL.end_date)
                .count_distinct_for_patient() - 1)
# Number of vaccinations during interval
measures_to_add['vax_app'] = (vaccinations.where(vaccinations
                                      .date
                                      .is_during(INTERVAL))
                                      .count_for_patient())
# Number of secondary care referrals during intervals
# Note that opa table is unsuitable for regional comparisons and 
# doesn't include mental health care and community services
measures_to_add['secondary_referral'] = (opa_cost.where(opa_cost
                                                        .referral_request_received_date
                                                        .is_during(INTERVAL))
                                                        .count_for_patient())

# Count number of appointments with cancelled/waiting status during interval
app_status_code = ['Cancelled by Unit','Waiting']
app_status_measure = ['cancelled_app', 'waiting_app']
for status_code, status_measure in zip(app_status_code, app_status_measure):
    measures_to_add[status_measure] = ((appointments.status
                    .is_in([status_measure])) &
                    (appointments.start_date
                    .is_during(INTERVAL))
                    ).count_distinct_for_patient()

# Adding rate of analgesic, antidepressant or antibiotic prescribing
measures_to_add['analgesic_pres'] = 0
# Count the number of prescriptions for each drug type, iteratively
for medication in med_dict.keys():
    # Antidepressants codelist uses snomedct, so use clinical events instead of medications table
    if medication == "antidepressant_pres":
        measures_to_add[medication] = (clinical_events.where((clinical_events
                                                     .snomedct_code
                                                     .is_in(med_dict[medication]))
                                                     & (clinical_events
                                                        .date
                                                        .is_during(INTERVAL)))
                                                     ).count_for_patient()
    else:
        measures_to_add[medication] = (medications.where((medications
                                                     .dmd_code
                                                     .is_in(med_dict[medication]))
                                                     & (medications
                                                        .date
                                                        .is_during(INTERVAL)))
                                                     ).count_for_patient()
    # Aggregate the analgesic subtypes into a single, broader analgesic measure
    if medication.startswith('analgesic'):
        measures_to_add['analgesic_pres'] += measures_to_add[medication]
        # Drop the analgesic subtype measures
        measures_to_add.pop(medication)

# Adding reason for appointment (inferred from appointment and reason being on the same day)
event_count = 0
for reason in app_reason_dict.keys():
    for day in range(0,7):
        # Iterate over each day of the interval (week)
        current_day = INTERVAL.start_date + days(day)
        # Extracting events that occured on that day
        event = (clinical_events.where(clinical_events
                                        .date.is_on_or_between(current_day, current_day))
                                        .where(clinical_events.where(clinical_events
                                        .date.is_on_or_between(current_day, current_day))
                .snomedct_code
                .is_in(app_reason_dict[reason]))
                .sort_by(clinical_events.date)
                .first_for_patient()
                )
        # Extracting appointments that occured on that day
        appointment = (valid_appointments.where(valid_appointments.start_date
                    .is_on_or_between(current_day, current_day))
                    .sort_by(valid_appointments.start_date)
                    .first_for_patient()
                    )
        # Adding up the events that occured on the same day as an appointment 
        # (inferring appointment reason) across each day of the interval/week
        event_count = (clinical_events.where(event.date == appointment.start_date)
                       .count_for_patient()) + event_count
    # Storing the count for the number of appointments for the given reason for the interval/week
    measures_to_add[reason] = event_count

# Defining measures ---
measures.define_defaults(
    denominator= was_female_or_male & age_filter & was_alive & 
                was_registered & has_deprivation_index & has_region & 
                prior_registration,
    group_by={
        "age": age_group,
        "sex": patients.sex,
        "ethnicity": ethnicity,
        "imd_quintile": imd_quintile,
        "carehome": carehome,
        "region": region,
        "rur_urb_class": rur_urb_class,
        "practice_pseudo_id": practice_id,
        "comorbid_chronic_resp": comorbid_chronic_resp,
        "comorbid_copd": comorbid_copd,
        "comorbid_asthma": comorbid_asthma,
        "comorbid_mh": comorbid_mental_health,
        "comorbid_neuro": comorbid_neuro
#        "vax_flu_12m": vax_status['influenza'], Need to check vaccine target disease is correct
#        "vax_covid_12m": vax_status['covid']
    },
    intervals=weeks(6).starting_on(study_start_date),
)

# Adding measures
for measure in measures_to_add.keys():
    measures.define_measure(
        name=measure,
        numerator=measures_to_add[measure],
    )