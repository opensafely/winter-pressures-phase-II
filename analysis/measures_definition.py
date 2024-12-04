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
study_reg_date = "2021-12-03"

# Demogragic codelists
ethnicity = codelist_from_csv(
    "codelists/opensafely-ethnicity.csv",
    column="Code",
    category_column="Grouping_6",
)

# Appointment reasons codelist:
app_reason_dict = {
    "resp_ill": "codelists/opensafely-acute-respiratory-illness-primary-care.csv", # not a good codelist 
    "pneum_broad": "codelists/bristol-pneumonia.csv",
    "neurological_app": "codelists/ons-neurological-disorders.csv",
    "sick_notes_app": "codelists/opensafely-sick-notes-snomed.csv"
}
app_reason_dict = create_codelist_dict(app_reason_dict)

# Append additional appointment reasons with SNOMED codes (no codelists); more specific top- usgae codes 
app_reason_dict["back_pain"] = ['279039007', '161891005', '161894002', '278860009', '279040009']
# Top usage codes for chest infection, without indication viral or bacterial. Search terms: respiratory infection | respiratory tract infection.
# Pneumonia excluded for specificity to conditions which may not neccessairly trigger Abx
app_reason_dict["chest_inf"] = ['50417007', '54150009', '195742007', '54398005', '448739000']
# Top pneumonia specific codes
app_reason_dict["pneum"] = ['233604007', '385093006', '312342009', '425464007', '278516003']

indication_dict = {"back_pain_opioid": app_reason_dict["back_pain"], 
                   "chest_inf_abx": app_reason_dict["chest_inf"],
                   "pneum_abx": app_reason_dict["pneum"]}

# Medications codelists:
med_dict ={
    "antidepressant_pres":"codelists/bristol-antidepressants-snomedct.csv",
    "antibiotic_pres":"codelists/opensafely-antibacterials.csv",
    "opioid_nasal":"codelists/opensafely-opioid-containing-medicines-buccal-nasal-and-oromucosal-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_inhale":"codelists/opensafely-opioid-containing-medicines-inhalation-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_oral":"codelists/opensafely-opioid-containing-medicines-oral-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_parental":"codelists/opensafely-opioid-containing-medicines-parenteral-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_rectal":"codelists/opensafely-opioid-containing-medicines-rectal-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_transdermal":"codelists/opensafely-opioid-containing-medicines-transdermal-excluding-drugs-for-substance-misuse-dmd.csv",
    "chest_abx": "codelists/user-arinat-chest-abx-dmd.csv"
}
med_dict = create_codelist_dict(med_dict)

prescription_dict = {key: med_dict[key] for key in ["opioid_oral", "chest_abx", "chest_abx"]}
# double coded of chest_Abx to match indication_dict for a loop later down

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
    "neuro": "codelists/primis-covid19-vacc-uptake-cns_cov.csv",
    "immuno_sup": "codelists/nhsd-immunosupression-pcdcluster-snomed-ct.csv"
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
    when((age >= 18) & (age < 40)).then("adult_over40"),
    when((age >= 40) & (age < 65)).then("adult_over65"),
    when((age >= 65) & (age < 80)).then("adult_over80"),
    when((age >= 80) & (age < 111)).then("adult_over80")
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

# Chronic resp disease (no resolution codelist). True if disease developed before interval start, else False.
comorbid_chronic_resp = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["chronic_resp"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .exists_for_patient()
)

# COPD (with resolution codelist). 
## Last COPD diagnosis date before interval start
comorbid_copd_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["copd"]) &
        clinical_events.date.is_on_or_before(INTERVAL.start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

# Last COPD resolution date before interval start
comorbid_copd_res_date_last = ( 
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["copd_res"]) &
        clinical_events.date.is_on_or_before(INTERVAL.start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

## True if COPD developed before interval start & never resolved OR resolved but recurred before the interval; else False
comorbid_copd = (
    comorbid_copd_date_last.is_not_null() & 
    (comorbid_copd_res_date_last.is_null() | (comorbid_copd_res_date_last < comorbid_copd_date_last))
).when_null_then(False)

# Asthma (with resolution codelist).
## Last asthma diagnosis date before interval start
comorbid_asthma_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["asthma"]) &
        clinical_events.date.is_on_or_before(INTERVAL.start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

## Last asthma resolution date before interval start
comorbid_asthma_res_date_last = ( 
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["asthma_res"]) &
        clinical_events.date.is_on_or_before(INTERVAL.start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .date
)

## True if asthma developed before interval start & never resolved OR resolved but recurred before the interval; else False
comorbid_asthma = (
    comorbid_asthma_date_last.is_not_null() & 
    (comorbid_asthma_res_date_last.is_null() | (comorbid_asthma_res_date_last < comorbid_asthma_date_last))
).when_null_then(False)

# Diabetes (with resolution codelist)
## Last diabetes diagnosis date before interval start
comorbid_dm_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["diabetes"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## Last diabetes resolution date before interval start
comorbid_dm_res_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["diabetes_res"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## True if diabetes developed before interval start & never resolved OR resolved but recurred before the interval start; else False
comorbid_dm = (
    comorbid_dm_date_last.is_not_null() &
    (comorbid_dm_res_date_last.is_null() | (comorbid_dm_res_date_last < comorbid_dm_date_last))
).when_null_then(False)

# Hypertension (with resolution codelist)
## Last hypertension diagnosis date before interval start
comorbid_htn_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["htn"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## Last hypertension resolution date before interval start
comorbid_htn_res_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["htn_res"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## True if hypertension developed before interval start & never resolved OR resolved but recurred before the interval start; else False
comorbid_htn = (
    comorbid_htn_date_last.is_not_null() &
    (comorbid_htn_res_date_last.is_null() | (comorbid_htn_res_date_last < comorbid_htn_date_last))
).when_null_then(False)

# Depression (with resolution codelist)
## Last depression diagnosis date before interval start
comorbid_depres_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["depres"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## Last depression resolution date before interval start
comorbid_depres_res_date_last = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["depres_res"]) &
                          clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .sort_by(clinical_events.date)
                          .last_for_patient()
                          .date
)

## True if depression developed before interval start & never resolved OR resolved but recurred before the interval start; else False
comorbid_depres = (
    comorbid_depres_date_last.is_not_null() &
    (comorbid_depres_res_date_last.is_null() | (comorbid_depres_res_date_last < comorbid_depres_date_last))
).when_null_then(False)

# Chronic mental health disease (no resolution codelist). True if disease developed before interval start; else False
comorbid_mh = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["mental_health"])
                          & clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .exists_for_patient()
)

# Chronic neurological disease (no resolution codelist). True if disease developed before interval start; else False
comorbid_neuro = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["neuro"])
                          & clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .exists_for_patient()
)

# Immunosupression (no resolution codelist). True if disease developed before interval start; else False
comorbid_immuno = (
    clinical_events.where(clinical_events.snomedct_code.is_in(comorbid_dict["immuno_sup"])
                          & clinical_events.date.is_on_or_before(INTERVAL.start_date))
                          .exists_for_patient()
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

measures_to_add['all_appointments_in_interval'] = (appointments.start_date
                            .is_during(INTERVAL)
                            .count_distinct_for_patient())
# Number of follow-up appointments:

appointments.app_prev_week = (appointments.where(
                (appointments.start_date
                .is_on_or_between(INTERVAL.start_date - days(7), INTERVAL.start_date - days(1))) &
                (appointments.seen_date == appointments.start_date)
                ).exists_for_patient()
                )
appointments.app_curr_week = (appointments.where(
                (appointments.start_date.is_during(INTERVAL)) &
                (appointments.seen_date == appointments.start_date)
                ).exists_for_patient()
                )

measures_to_add["follow_up_app"] = (appointments.where(
                                    appointments.app_prev_week & appointments.app_curr_week)
                                    .exists_for_patient())

# Number of vaccinations during interval, all and for flu and covid
measures_to_add['vax_app'] = (vaccinations.where(vaccinations
                                      .date
                                      .is_during(INTERVAL))
                                      .count_for_patient())
measures_to_add['vax_app_flu'] = (vaccinations.where(
    vaccinations.target_disease.is_in(['INFLUENZA']) &
    vaccinations.date.is_during(INTERVAL))
    .count_for_patient())
measures_to_add['vax_app_covid'] = (vaccinations.where(
    vaccinations.target_disease.is_in(['SARS-2 CORONAVIRUS']) &
    vaccinations.date.is_during(INTERVAL))
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
    measures_to_add[status_measure] = (appointments.where((appointments.status == status_code) &
                    (appointments.start_date
                    .is_during(INTERVAL))
                    )).count_for_patient()

# Adding rate of opioid, antidepressant or antibiotic prescribing
measures_to_add['opioid_pres'] = 0
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
    # Aggregate the opioid subtypes into a single, broader opioid measure
    if medication.startswith('opioid'):
        measures_to_add['opioid_pres'] += measures_to_add[medication]
        # Drop the opioid subtype measures
        measures_to_add.pop(medication)

# Adding reason for appointment (inferred from appointment and reason being on the same day)
for reason in app_reason_dict.keys():
    event = (clinical_events.where((clinical_events
                                    .snomedct_code
                                    .is_in(app_reason_dict[reason]))
                                    & (clinical_events
                                        .date
                                        .is_during(INTERVAL))
                                        )
            )
    measures_to_add[reason] = (event.where(event.date.is_in(valid_appointments.start_date))
                       .count_for_patient()
                )

# Adding appointments with indication & prescription 
for indication, prescription in zip (indication_dict.keys(), prescription_dict.keys()) :
    event = (clinical_events.where((clinical_events
                                    .snomedct_code
                                    .is_in(indication_dict[indication]))
                                    & (clinical_events
                                        .date
                                        .is_during(INTERVAL))
                                        )
            )
    prescription = (medications.where((medications.dmd_code.is_in(prescription_dict[prescription]))
                                    & (medications.date.is_during(INTERVAL)))
                    )
    measures_to_add[indication] = ((event.where((event.date.is_in(valid_appointments.start_date))
                                            & (event.date.is_in(prescription.date))))
                                            .count_for_patient())

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
    intervals=weeks(6).starting_on(study_start_date),
)

# Adding measures
for measure in measures_to_add.keys():
    measures.define_measure(
        name=measure,
        numerator=measures_to_add[measure],
    )
