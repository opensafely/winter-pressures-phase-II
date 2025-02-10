# TODO:
# Potentially refactor to use classes when time available

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
def count_secondary_referral(interval_start, interval_end): 
    '''
    Counts the number of secondary care referrals. Outpatient appointments 
    data is provided via the NHS Secondary Uses Service.
    No args
    Returns:
        Count of secondary referrals in interval
    '''
    secondary_referral_count = (opa_cost.where(opa_cost
                    .referral_request_received_date
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
    appointments.app_prev_week = (appointments.where(
                (appointments.seen_date
                .is_on_or_between(interval_start - days(7), interval_start - days(1)))
                ).exists_for_patient()
                )
    appointments.app_curr_week = seen_appts_in_interval.exists_for_patient()

    follow_up = (appointments.where(
                        appointments.app_prev_week & appointments.app_curr_week)
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