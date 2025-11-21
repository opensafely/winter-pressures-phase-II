# This script defines the measures for the analysis pipeline.

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
    claim_permissions,
    minimum_of,
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
    ethnicity_from_sus,
)
from queries import *
from codelist_definition import *
from wp_config_setup import args

claim_permissions("appointments")

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=100)
measures.configure_disclosure_control(enabled=False)
if args.test == True:
    NUM_WEEKS = 6
else:
    NUM_WEEKS = 52

#  ---------------------- Inclusion criteria --------------------------------

# Age 0 - 110 (as per WP2)
age_at_interval_start = patients.age_on(INTERVAL.start_date)
age_filter = (age_at_interval_start >= 0) & (age_at_interval_start <= 110)

# Alive throughout at the beginning (avoids immortal patient bias)
was_alive = patients.is_alive_on(INTERVAL.start_date)

# Registered at the start of the interval and
# only include practices that became TPP before the interval being measured
was_registered = (
    practice_registrations.exists_for_patient_on(INTERVAL.start_date)
    & practice_registrations.where(
        practice_registrations.practice_systmone_go_live_date <= INTERVAL.start_date
    ).exists_for_patient()
)

# No missing data: known sex
has_known_sex = patients.sex.is_in(["female", "male", "intersex"])

# ---------------------- Patient subgroups --------------------------------

# Age subgroups
age = age_at_interval_start
age_group = case(
    when((age >= 0) & (age < 5)).then("preschool"),
    when((age >= 5) & (age < 12)).then("primary_school"),
    when((age >= 12) & (age < 18)).then("secondary_school"),
    when((age >= 18) & (age < 45)).then("adult_under_45"),
    when((age >= 45) & (age < 65)).then("adult_under_65"),
    when((age >= 65) & (age < 75)).then("adult_under_75"),
    when((age >= 75) & (age < 80)).then("adult_under_80"),
    when((age >= 80) & (age < 111)).then("adult_80+"),
)

# Ethnicity
ethnicity = (
    clinical_events.where(clinical_events.snomedct_code.is_in(ethnicity))
    .where(clinical_events.date.is_on_or_before(INTERVAL.start_date))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .snomedct_code.to_category(ethnicity)
)

# Depravation
imd_rounded = addresses.for_patient_on(INTERVAL.start_date).imd_rounded
max_imd = 32844
# Otherwise condition captures all IMDs -1 which is equivalent to NULL in TPP
imd_quintile = case(
    when((imd_rounded >= 0) & (imd_rounded <= int(max_imd * 1 / 5))).then(1),
    when(imd_rounded <= int(max_imd * 2 / 5)).then(2),
    when(imd_rounded <= int(max_imd * 3 / 5)).then(3),
    when(imd_rounded <= int(max_imd * 4 / 5)).then(4),
    when(imd_rounded <= max_imd).then(5),
    otherwise=99,
)

# Care home residency
carehome = addresses.for_patient_on(INTERVAL.start_date).care_home_is_potential_match

# Defining interval events for reusability in later queries
interval_events = clinical_events.where(clinical_events.date.is_during(INTERVAL))

# Patient urban-rural classification
rur_urb_class = addresses.for_patient_on(INTERVAL.start_date).rural_urban_classification

# Practice data taken at the start of the interval
practice_id = practice_registrations.for_patient_on(
    INTERVAL.start_date
).practice_pseudo_id
region = practice_registrations.for_patient_on(
    INTERVAL.start_date
).practice_nuts1_region_name

# Vaccination status
vax_status = {}
for disease in [
    "INFLUENZA",
    "SARS-2 CORONAVIRUS",
    "PNEUMOCOCCAL",
    "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer)",
]:

    # Abrysvo is the vaccine name for rsv
    if "Abrysvo" in disease:
        vax_table_field = vaccinations.product_name
    else:
        vax_table_field = vaccinations.target_disease

    has_vax = vaccinations.where(vax_table_field.is_in([disease])).exists_for_patient()

    last_12_months = vaccinations.where(
        vaccinations.date.is_on_or_between(
            INTERVAL.start_date - years(1), INTERVAL.start_date
        )
    ).exists_for_patient()

    # Flu and covid give 12 months protection
    if disease in ["INFLUENZA", "SARS-2 CORONAVIRUS"]:
        vax_status[disease] = has_vax & last_12_months

    # Pneumococcal and RSV (Abrysvo) are lifetime vaccines
    elif disease in [
        "PNEUMOCOCCAL",
        "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer)",
    ]:
        vax_status[disease] = has_vax

# Co-morbidity
# Check if patient had a resolvable condition in the interval
comorbid_copd = check_resolved_condition(
    comorbid_dict["copd"], comorbid_dict["copd_res"], INTERVAL.start_date
)
comorbid_asthma = check_resolved_condition(
    comorbid_dict["asthma"], comorbid_dict["asthma_res"], INTERVAL.start_date
)
comorbid_dm = check_resolved_condition(
    comorbid_dict["diabetes"], comorbid_dict["diabetes_res"], INTERVAL.start_date
)
comorbid_htn = check_resolved_condition(
    comorbid_dict["htn"], comorbid_dict["htn_res"], INTERVAL.start_date
)

# Check if patient had an unresolvable (chronic) condition in the interval
comorbid_chronic_resp = check_chronic_condition(
    comorbid_dict["chronic_resp"], INTERVAL.start_date
)
comorbid_immuno = check_chronic_condition(
    comorbid_dict["immuno_sup"], INTERVAL.start_date
)

# ---------------------- Measures --------------------------------

measures_to_add = {}
# Valid appointments are those where seen_date is in interval
seen_appts_in_interval = create_seen_appts_in_interval(
    INTERVAL.start_date, INTERVAL.end_date
)

# Count number of consultations in interval
measures_to_add["online_consult"] = count_clinical_consultations(
    online_consult, "many_pp", INTERVAL.start_date, INTERVAL.end_date
)
measures_to_add["call_from_patient"] = count_clinical_consultations(
    "25691000000103", "many_pp", INTERVAL.start_date, INTERVAL.end_date
)
measures_to_add["call_from_gp"] = count_clinical_consultations(
    "24671000000101", "many_pp", INTERVAL.start_date, INTERVAL.end_date
)
measures_to_add["tele_consult"] = count_clinical_consultations(
    "386472008", "many_pp", INTERVAL.start_date, INTERVAL.end_date
)
measures_to_add["emergency_care"] = count_emergency_care_attendance(
    INTERVAL.start_date, INTERVAL.end_date
)

# Count sro measures in interval
for key in sro_dict.keys():
    measures_to_add[key] = count_clinical_consultations(
        sro_dict[key], "many_pp", INTERVAL.start_date, INTERVAL.end_date
    )

# Combine prioritized and deprioritized sro measures
measures_to_add["sro_prioritized"] = sum(
    [measures_to_add[sro] for sro in args.prioritized]
)
measures_to_add["sro_deprioritized"] = sum(
    [measures_to_add[sro] for sro in args.deprioritized]
)

# Number of appointments in interval
measures_to_add["seen_in_interval"] = count_seen_in_interval(seen_appts_in_interval)
measures_to_add["start_in_interval"] = count_start_in_interval(
    INTERVAL.start_date, INTERVAL.end_date
)

# Number of follow-up appointments in interval
measures_to_add["follow_up_app"] = count_follow_up(
    INTERVAL.start_date, seen_appts_in_interval
)

# Number of vaccinations during interval, all and for flu and covid
measures_to_add["vax_app"] = count_vaccinations(INTERVAL.start_date, INTERVAL.end_date)
measures_to_add["vax_app_flu"] = count_vaccinations(
    INTERVAL.start_date, INTERVAL.end_date, ["INFLUENZA"]
)
measures_to_add["vax_app_covid"] = count_vaccinations(
    INTERVAL.start_date, INTERVAL.end_date, ["SARS-2 CORONAVIRUS"]
)

# Number of secondary care referrals during intervals
# Note that opa table is unsuitable for regional comparisons and
# doesn't include mental health care and community services
measures_to_add["secondary_referral"] = count_secondary_referral(
    INTERVAL.start_date, INTERVAL.end_date, type="referral_date"
)
measures_to_add["secondary_appt"] = count_secondary_referral(
    INTERVAL.start_date, INTERVAL.end_date, type="appointment_date"
)

# Count number of appts for sick notes
measures_to_add["sick_notes_app"] = count_reason_for_app(
    INTERVAL.start_date,
    INTERVAL.end_date,
    app_reason_dict["sick_notes_app"],
    seen_appts_in_interval,
)

# Count number of appointments with cancelled/waiting status during interval
app_status_code = [
    "Did Not Attend",
    "Waiting",
    "Cancelled by Patient",
    "Cancelled by Unit",
]
app_status_measure = [status.replace(" ", "") for status in app_status_code]
for status_code, status_measure in zip(app_status_code, app_status_measure):
    measures_to_add[status_measure] = count_appointments_by_status(
        INTERVAL.start_date, INTERVAL.end_date, status_code
    )

# Configuration based on CLI arg. Add these measures if --add_measure flag called

if args.add_indicat_prescript == True:
    # Count appointments with an indication and prescription
    measures_to_add.update(
        appointments_with_indication_and_prescription(
            INTERVAL.start_date,
            INTERVAL.end_date,
            indication_dict,
            prescription_dict,
            seen_appts_in_interval,
        )
    )

if args.add_prescriptions == True:
    # Count prescriptions and add to measures
    measures_to_add.update(
        count_prescriptions(INTERVAL.start_date, INTERVAL.end_date, med_dict)
    )

if args.add_reason == True:
    # Adding reason for appointment (inferred from appointment and reason being on the same day)
    for reason in app_reason_dict.keys():
        measures_to_add[reason] = count_reason_for_app(
            INTERVAL.start_date,
            INTERVAL.end_date,
            app_reason_dict[reason],
            seen_appts_in_interval,
        )

# ---- SPECIFIC AND SENSITIVE SEASONAL ILLNESSES ------------------

# Max sensitivity

measures_to_add["flu_sensitive"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "flu",
    resp_dict["flu_sensitive"],
    flu_med_codelist,
    flu_sensitive_exclusion,
    resp_dict["flu_specific"],
)

measures_to_add["rsv_sensitive"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "rsv",
    resp_dict["rsv_sensitive"],
    rsv_med_codelist,
    rsv_sensitive_exclusion,
    resp_dict["rsv_specific"],
)

measures_to_add["covid_sensitive"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "covid",
    resp_dict["covid_sensitive"],
    covid_med_codelist,
    covid_sensitive_exclusion,
    resp_dict["covid_specific"],
)

measures_to_add["overall_resp_sensitive"] = count_mild_overall_resp_illness(
    INTERVAL.start_date,
    INTERVAL.end_date,
    measures_to_add["flu_sensitive"],
    measures_to_add["covid_sensitive"],
    measures_to_add["rsv_sensitive"],
    age,
)

# Limit to cases with appt in the same interval to reduce secondary discharge codes

measures_to_add["flu_sensitive_with_appt"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "flu",
    resp_dict["flu_sensitive"],
    flu_med_codelist,
    flu_sensitive_exclusion,
    resp_dict["flu_specific"],
    seen_appts_in_interval=seen_appts_in_interval,
)

measures_to_add["rsv_sensitive_with_appt"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "rsv",
    resp_dict["rsv_sensitive"],
    rsv_med_codelist,
    rsv_sensitive_exclusion,
    resp_dict["rsv_specific"],
    seen_appts_in_interval=seen_appts_in_interval,
)

measures_to_add["covid_sensitive_with_appt"] = count_seasonal_illness_sensitive(
    INTERVAL.start_date,
    INTERVAL.end_date,
    "covid",
    resp_dict["covid_sensitive"],
    covid_med_codelist,
    covid_sensitive_exclusion,
    resp_dict["covid_specific"],
    seen_appts_in_interval=seen_appts_in_interval,
)

measures_to_add["overall_resp_sensitive_with_appt"] = count_mild_overall_resp_illness(
    INTERVAL.start_date,
    INTERVAL.end_date,
    measures_to_add["flu_sensitive"],
    measures_to_add["covid_sensitive"],
    measures_to_add["rsv_sensitive"],
    age,
    seen_appts_in_interval=seen_appts_in_interval,
)

# Max specificity

for codelist in resp_dict.keys():
    if "specific" in codelist:
        measures_to_add[codelist] = count_clinical_consultations(
            resp_dict[codelist], "one_pp", INTERVAL.start_date, INTERVAL.end_date
        )

# ---------------------- Define measures --------------------------------

inclusion_criteria = has_known_sex & age_filter & was_alive & was_registered
intervals = weeks(NUM_WEEKS).starting_on(args.start_intv)

if args.demograph_measures:
    # Run patient script if patient flag called
    measures.define_defaults(
        denominator=inclusion_criteria,
        group_by={
            "age": age_group,
            "sex": patients.sex,
            "ethnicity": ethnicity,
            "ethnicity_sus": ethnicity_from_sus.code,
            "imd_quintile": imd_quintile,
            "carehome": carehome,
            "region": region,
            "rur_urb_class": rur_urb_class,
        },
        intervals=intervals,
    )
elif args.practice_measures:
    # Run practice script if practice flag called
    measures.define_defaults(
        denominator=inclusion_criteria,
        group_by={"practice_pseudo_id": practice_id},
        intervals=intervals,
    )
elif args.comorbid_measures:
    # Run comorbid script if comorbid flag called
    measures.define_defaults(
        denominator=inclusion_criteria,
        group_by={
            "age": age_group,
            "comorbid_chronic_resp": comorbid_chronic_resp,
            "comorbid_copd": comorbid_copd,
            "comorbid_asthma": comorbid_asthma,
            "comorbid_dm": comorbid_dm,
            "comorbid_htn": comorbid_htn,
            "comorbid_immuno": comorbid_immuno,
            "vax_flu_12m": vax_status["INFLUENZA"],
            "vax_covid_12m": vax_status["SARS-2 CORONAVIRUS"],
            "vax_pneum_ever": vax_status["PNEUMOCOCCAL"],
            "vax_rsv_ever": vax_status[
                "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer)"
            ],
        },
        intervals=intervals,
    )

# Filtering out measures to select pipeline

if args.set == "resp":
    for key in list(measures_to_add.keys()):
        if ("sensitive" not in key) and ("specific" not in key) and (
            key not in [
                "secondary_referral",
                "secondary_appt",
            ]
        ):
            del measures_to_add[key]

if args.set == "sro":
    for key in list(measures_to_add.keys()):
        if (key not in sro_dict) and (
            key not in [
                "sick_notes_app",
                "sro_prioritized",
                "sro_deprioritized",
            ]
        ):
            del measures_to_add[key]

# Adding measures
for measure in measures_to_add.keys():
    measures.define_measure(
        name=measure,
        numerator=measures_to_add[measure],
    )
