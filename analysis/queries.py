# This script contains the ehrql queries for measures definition and test dataset definition.

from ehrql import case, codelist_from_csv, create_dataset, days, weeks, years, when, INTERVAL, create_measures
from ehrql.tables.core import medications, patients
from ehrql.tables.tpp import (
    addresses,
    opa_cost,
    clinical_events,
    practice_registrations,
    appointments,
    vaccinations,
    emergency_care_attendances
)

def create_seen_appts_in_interval(interval_start, interval_end):
    '''
    Filters the appointments table to only contain appointments
    where seen date is within the interval.
    No args
    Returns:
        Filtered appointment table
    '''
    return appointments.where(appointments.seen_date.is_on_or_between(interval_start, interval_end))
    
# Note that all below measures use intervals as arguments
def count_secondary_referral(interval_start, interval_end, type): 
    '''
    Counts the number of secondary care referrals. Outpatient appointments 
    data is provided via the NHS Secondary Uses Service.
    Args:
        type: 'referral_date' or 'appointment_date'
    Returns:
        Count of secondary referrals in interval. One per patient for referral date;
        multiple per patient for appointment date
    '''
    if type == "referral_date":    
        secondary_referral_count = (opa_cost.where(opa_cost
                        .referral_request_received_date
                        .is_on_or_between(interval_start, interval_end))
                        .exists_for_patient())
        
    elif type == "appointment_date":
        secondary_referral_count = (opa_cost.where(opa_cost
                        .appointment_date 
                        .is_on_or_between(interval_start, interval_end))
                        .count_for_patient())
    
    return secondary_referral_count

def count_follow_up(interval_start, seen_appts_in_interval):
    '''
    Counts the number of patients who had a follow up appointment,
    defined as a patient who had an appointment in the current interval,
    and the an appointment in the week prior to the interval.
    Args:
        seen_appts_in_interval: appointments table with seen date in interval
    Returns:
        Count of number of patients who had a follow up appointment 
        in the interval
    '''
    appointments.app_prev_month = (appointments.where(
                (appointments.seen_date
                .is_on_or_between(interval_start - days(31), interval_start - days(1)))
                ).exists_for_patient()
                )
    appointments.app_curr_week = seen_appts_in_interval.exists_for_patient()

    follow_up = (appointments.where(
                        appointments.app_prev_month & appointments.app_curr_week)
                        .exists_for_patient())
    return follow_up

def count_reason_for_app(interval_start, interval_end, reason, seen_appts_in_interval):
    '''
    Counts the number of appointments for different clinical events,
    where reason and event are assumed to be linked if they have the same date
    Args:
        reason: clinical event that could be linked to appointment
        seen_appts_in_interval: appointments with seen date in interval
    Returns:
        Count of number of appointments for each reason
    '''
    event = (clinical_events.where((clinical_events
                                    .snomedct_code
                                    .is_in(reason))
                                    & (clinical_events
                                        .date
                                        .is_on_or_between(interval_start, interval_end))
                                        )
            )
    result = (event.where(event.date.is_in(seen_appts_in_interval.start_date))
                       .count_for_patient()
                )
    return result

def count_seen_in_interval(seen_appts_in_interval):
    """
    Counts the number of appointments during the interval using seen date.
    Args:
        seen_appts_in_interval: Appointments with seen date in the interval.
    Returns:
        The count of appointments per patient.
    """
    return seen_appts_in_interval.count_for_patient()

def count_start_in_interval(interval_start, interval_end):
    """
    Counts the number of appointments during the interval using start date.
    Args:
        seen_appts_in_interval: Appointments with start date in the interval.
    Returns:
        The count of appointments per patient.
    """
    return appointments.where(
        appointments.start_date.is_on_or_between(interval_start, interval_end)
    ).count_for_patient()

def count_vaccinations(interval_start, interval_end, target_disease=None):
    """
    Counts vaccinations during the interval, optionally filtered by target disease.
    Args:
        target_disease: A list of diseases to filter by (e.g., 'INFLUENZA', 'SARS-2 CORONAVIRUS').
    Returns:
        The count of vaccinations per patient.
    """
    filtered_vaccinations = vaccinations.where(
        vaccinations.date.is_on_or_between(interval_start, interval_end)
    )
    if target_disease:
        filtered_vaccinations = filtered_vaccinations.where(
            vaccinations.target_disease.is_in(target_disease)
        )
    return filtered_vaccinations.count_for_patient()

def count_appointments_by_status(interval_start, interval_end, status_code):
    """
    Counts appointments with a specific status during the interval.
    Args:
        status_code: The status code to filter appointments by (e.g., 'Cancelled by Unit').
    Returns:
        The count of appointments per patient with the specified status.
    """
    return appointments.where(
        (appointments.status == status_code)
        & appointments.start_date.is_on_or_between(interval_start, interval_end)
    ).count_for_patient()

def count_prescriptions(interval_start, interval_end, med_dict):
    """
    Counts prescriptions for each drug category and aggregates analgesic subtypes.
    Args:
        med_dict: Dictionary mapping drug categories to their corresponding codes.
    Returns:
        A dictionary of prescription counts per patient.
    """
    measures = {}
    opioid_total = 0  # For aggregating analgesic subtypes

    for medication, codes in med_dict.items():
        if medication == "antidepressant_pres":
            # Use clinical_events for antidepressants
            # because antidepressant codelist uses SNOMED
            measure_count = clinical_events.where(
                (clinical_events.snomedct_code.is_in(codes))
                & clinical_events.date.is_on_or_between(interval_start, interval_end)
            ).count_for_patient()
        else:
            # Use medications for other drugs (mostly analgesics)
            # because their codelists use dmd
            measure_count = medications.where(
                (medications.dmd_code.is_in(codes))
                & medications.date.is_on_or_between(interval_start, interval_end)
            ).count_for_patient()

        measures[medication] = measure_count

        # If it's an analgesic subtype, add to the total and remove its subtype measure
        if medication.startswith('opioid'):
            opioid_total += measure_count
            del measures[medication]

    # Add the aggregated analgesic measure
    measures['opioid_pres'] = opioid_total

    return measures

def appointments_with_indication_and_prescription(interval_start, interval_end, indication_dict, prescription_dict, seen_appts_in_interval):
    """
    Calculate appointments with an indication and a corresponding prescription.
    
    Parameters:
        indication_dict: Dictionary mapping indications to their respective clinical codes.
        prescription_dict: Dictionary mapping prescription types to their respective medication codes.
        seen_appts_in_interval: Appointments with seen date in the interval.
        
    Returns:
        A dictionary with indication keys and counts of appointments matching the criteria.
    """
    measures = {}

    for indication, prescription in zip(indication_dict.keys(), prescription_dict.keys()):
        # Filter clinical events by indication
        event = (clinical_events.where((clinical_events.snomedct_code.is_in(indication_dict[indication])) &
                                       (clinical_events.date.is_on_or_between(interval_start, interval_end))))

        # Filter medications by prescription
        prescription_events = (medications.where((medications.dmd_code.is_in(prescription_dict[prescription])) &
                                                 (medications.date.is_on_or_between(interval_start, interval_end))))

        # Count appointments that match both criteria
        measures[indication] = (event.where((event.date.is_in(seen_appts_in_interval.start_date)) &
                                            (event.date.is_in(prescription_events.date)))
                                .count_for_patient())
    
    return measures

def check_chronic_condition(codelist, interval_start):
    """
    Checks if a chronic condition exists before the interval start.
    These are chronic so resolved codes are unavailable.
    Args:
        codelist: Codelist for chronic condition
    Returns:
        Binary indicator of whether the code exists for the patient
    """
    return clinical_events.where(
        clinical_events.snomedct_code.is_in(codelist) &
        clinical_events.date.is_on_or_before(interval_start)
    ).exists_for_patient()

def get_last_event_date(codelist, interval_start):
    """
    Gets the last event date for a condition before the interval start.
    Args:
        codelist: Codelist for condition
    Returns:
        Date of last entry for that code for a patient
    """
    return clinical_events.where(
        clinical_events.snomedct_code.is_in(codelist) &
        clinical_events.date.is_on_or_before(interval_start)
    ).sort_by(clinical_events.date).last_for_patient().date

def check_resolved_condition(diagnosis_codelist, resolution_codelist, interval_start):
    """
    Checks if a condition developed before the interval start and has not resolved.
    Args:
        diagnosis_codelist: Diagnosis codelist for condition
        resolution_codelist: Resolution codelist for condition
    Returns:
        Binary indicator of whether the patient has the unresolved condition
    """
    last_diagnosis_date = get_last_event_date(diagnosis_codelist, interval_start)
    last_resolution_date = get_last_event_date(resolution_codelist, interval_start)

    return (
        last_diagnosis_date.is_not_null() &
        (
            last_resolution_date.is_null() | 
            (last_resolution_date < last_diagnosis_date)
        )
    ).when_null_then(False)

def count_clinical_consultations(code, interval_start, interval_end):
    """
    Counts consultations during the interval.
    Args:
        code: Code or list of codes for interaction
    Returns:
        The count of consultations per patient.
    """
    # If a single code is given rather than a codelist, parse the code as a list
    if isinstance(code, str):
        code = [code]

    return clinical_events.where(clinical_events.snomedct_code.is_in(code)
                                  & clinical_events.date.is_on_or_between(interval_start, interval_end)).count_for_patient()

def count_emergency_care_attendance(interval_start, interval_end):
    """
    Counts emergency care attendances during the interval.
    Returns:
        The count of emergency care attendances per patient.
    """
    return emergency_care_attendances.where(emergency_care_attendances
                                            .arrival_date
                                            .is_on_or_between(interval_start, interval_end)
                                            ).count_for_patient()

# def count_influenza_like_illness(interval_start, interval_end, 
#                                  maximally_specific_codes,
#                                  maximally_sensitive_codes,
#                                  ARI_codes,
#                                  fever_codes,
#                                  antiviral_codes,
#                                  exclusion_codes):
#     """
#     Counts influenza-like illness (ILI) events meeting 'maximally sensitive' criteria.
#     """

#     # Limit to events in interval
#     events = clinical_events.where(clinical_events.date.is_on_or_between(interval_start, interval_end))
#     meds = medications.where(medications.date.is_on_or_between(interval_start, interval_end))

#     # ---------------- Inclusion criteria ----------------

#     # 1. Maximally specific event
#     specific_events = events.where(events.snomedct_code.is_in(maximally_specific_codes))

#     # 2. Maximally sensitive event
#     sensitive_events = events.where(events.snomedct_code.is_in(maximally_sensitive_codes))

#     # Exclusion events
#     exclusion_events = events.where(events.snomedct_code.is_in(exclusion_codes))

#     # 3. Influenza-like illness = Respiratory illness + fever ≥ 38°C within same episode (±14 days)
#     ARI_events = events.where(events.snomedct_code.is_in(ARI_codes))
#     fever_events = events.where(events.snomedct_code.is_in(fever_codes))

#     # ILI_codes (with duplicates) = ari_event in interval & fever within 14 days 
#     # ILI_codes (without duplicates) = first_for_patient(ILI_codes (with duplicates))
#     ILI_events = ARI_events.where(
#         fever_events.where(
#             (ARI_events.sort_by(ARI_events.date.first_for_patient().date)
#              -fever_events.sort_by(fever_events.date..date)).days 
#              <= days(14))
#     ).first_for_patient()

#     # 4. Antiviral prescription
#     antiviral_rx = meds.where(meds.dmd_code.is_in(antiviral_codes))

#     meets_inclusion = (
#         specific_event.exists_for_patient() |
#         influenza_event.exists_for_patient() |
#         respiratory_with_fever |
#         antiviral_rx.exists_for_patient()
#     )

#     # ---------------- Exclusion criteria ----------------

#     within_exclusion_window = exclusion_events.where(
#         (exclusion_events.date - ARI_events.date).days <= days(30)) |
#         ((exclusion_events.date - antiviral_rx.date).days <= days(30))
#     )

#     # ---------------- Combine ----------------
#     return meets_inclusion & ~within_exclusion_window

def filter_events_in_interval(interval_start, interval_end, codelist):
    '''
    Filter the events from a given codelist and interval
    Args:
        codelist
    Returns:
        EventFrame
    '''
    return clinical_events.where(clinical_events.snomedct_code.is_in(codelist)
                                  & clinical_events.date.is_on_or_between(interval_start, interval_end)
                                  )

def count_seasonal_illness_sensitive(interval_start, interval_end, disease, codelist_ari, codelist_fever, 
                                     codelist_max_sens, codelist_med, codelist_exclusion, codelist_max_spec, 
                                     seen_appts_in_interval = None):
    '''
    Counts the number of patients who had a flu, identified with maximal sensitivity
    Args:
        disease: flu, rsv or covid
        codelist_ari: Acute Respiratory Disease codelist
        codelist_fever: Fever codelist
        codelist_max_sens: Max sensitivity flu codelist
        codelist_med: Flu antiviral codelist
        codelist_exclusion: Non-flu respiratory illness
        codelist_max_spec: Max specificity rsv codelist
        seen_appts_in_interval: Filtered appointments table, used if filtering events to those paired with an appt
    Returns:
        Count the number of patients who had a flu case
    '''

    # Max specificity event
    has_max_spec_event = (filter_events_in_interval(interval_start, interval_end, codelist_max_spec)
                                      .exists_for_patient())

    # Max sensitivity event
    max_sens_event_count = (filter_events_in_interval(interval_start, interval_end, codelist_max_sens)
                                      .count_for_patient())
    
    # Antiviral prescription
    has_antiviral_prescription = medications.where(
                        (medications.dmd_code.is_in(codelist_med))
                            & medications.date.is_on_or_between(interval_start, interval_end)
                        ).exists_for_patient()
    
    # Exclusion criteria
    has_exclusion = (filter_events_in_interval(interval_start - weeks(2), interval_end + weeks(2), codelist_exclusion)
                                 .exists_for_patient())
    
    if (disease == 'rsv') | (disease == 'covid'):

        max_sens_event_date = (filter_events_in_interval(interval_start, interval_end, codelist_max_sens)
                                                .sort_by(clinical_events.date)
                                                .first_for_patient()
                                                .date)
        
        has_max_sens_event2 = (filter_events_in_interval(max_sens_event_date + days(1), 
                                                                    max_sens_event_date + days(1) + weeks(2), 
                                                                    codelist_max_sens)
                                        .exists_for_patient())

        # (Max specificity RSV OR 2 Max sensitivity RSV OR [1 Max sensitivity RSV AND antiviral prescription]) 
        # AND NOT other non-flu respiratory illness (e.g. covid)
        has_max_sensitivity = (
            (has_max_spec_event | (max_sens_event_count >= 2) | ((max_sens_event_count == 1) & has_max_sens_event2) | ((max_sens_event_count >= 1) & has_antiviral_prescription))
            & ~(has_exclusion)
        )

    if disease == 'flu':

        # ILI 1 - ARI and then fever in same episode
        has_ari_symptom_this_week = (filter_events_in_interval(interval_start, interval_end, codelist_ari)
                                                .exists_for_patient())
        
        ari_date_this_week = (filter_events_in_interval(interval_start, interval_end, codelist_ari)
                                            .sort_by(clinical_events.date)
                                            .last_for_patient()
                                            .date)

        has_fever_symptom_next_2_weeks = (filter_events_in_interval(ari_date_this_week, ari_date_this_week + weeks(2), codelist_fever)
                                                    .exists_for_patient())

        # ILI 2 - fever and then ALI in same episode
        has_fever_symptom_this_week = (filter_events_in_interval(interval_start, interval_end, codelist_fever)
                                                .exists_for_patient())
        
        fever_date_this_week = (filter_events_in_interval(interval_start, interval_end, codelist_fever)
                                            .sort_by(clinical_events.date)
                                            .last_for_patient()
                                            .date)

        has_ari_symptom_next_2_weeks = (filter_events_in_interval(fever_date_this_week, fever_date_this_week + weeks(2), codelist_ari)
                                                    .exists_for_patient())

        # ILI overall - Either ari and then fever, or fever and then ari
        has_ili = (
            (has_ari_symptom_this_week & has_fever_symptom_next_2_weeks) |
            (has_fever_symptom_this_week & has_ari_symptom_next_2_weeks)
        )

        # Max sensitive flu = (ILI, flu code, or flu medication) AND not a different respiratory illness
        has_max_sensitivity = (((has_ili) | (max_sens_event_count >= 1) | (has_antiviral_prescription))
                                & (~(has_exclusion)))
    
    if seen_appts_in_interval != None:

        has_appt_in_interval = seen_appts_in_interval.exists_for_patient()

        has_max_sensitivity = has_max_sensitivity & has_appt_in_interval

    return has_max_sensitivity

def count_mild_overall_resp_illness(interval_start, interval_end, has_flu, has_covid, has_rsv, age,
                                    codelist_overall_max_sens, codelist_exclusion, asthma_copd_exacerbation_codelist,
                                    seen_appts_in_interval = None):
    '''
    Count patients with (flu OR RSV or covid OR an unidentified resp illness OR [excerbation AND older]) 
    AND NOT exclusion criteria
    Args:
        has_flu/covid/rsv: BoolPatientSeries of max sensitivity cases
        age: IntPatientSeries of age of each patient
        codelist_overall_max_sens: codelist for unidentified resp illness
        codelist_exclusion: codelist for exclusion criteria (i.e. other non-respiratory illnesses)
        asthma_copd_exacerbation_codelist: codelist for ashma and copd exacerbation for the elderly
        seen_appts_in_interval: Filtered appointments table, used if filtering events to those paired with an appt
    Returns:
        has_max_sens_overall_resp_ill: BoolPatientSeries of any respiratory illness at max sensitivity
    '''

    has_overall_max_sens = (filter_events_in_interval(interval_start, interval_end, codelist_overall_max_sens)
                                                .exists_for_patient())
    
    has_exclusion = (filter_events_in_interval(interval_start - weeks(2), interval_end + weeks(2), codelist_exclusion)
                                 .exists_for_patient())
    
    has_exacerbation = (filter_events_in_interval(interval_start, interval_end, asthma_copd_exacerbation_codelist)
                                                .exists_for_patient())
    
    is_older = age >= 65 
    
    # Count patients with (flu OR RSV or covid OR an unidentified resp illness OR [excerbation AND older]) AND NOT exclusion criteria

    has_max_sens_overall_resp_ill = ((has_flu | has_covid | has_rsv | has_overall_max_sens | (has_exacerbation & is_older))
                                     & ~(has_exclusion))
    
    if seen_appts_in_interval != None:

        has_appt_in_interval = seen_appts_in_interval.exists_for_patient()

        has_max_sens_overall_resp_ill = has_max_sens_overall_resp_ill & has_appt_in_interval

    return has_max_sens_overall_resp_ill
