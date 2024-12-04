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

# Date specifications
study_start_date = "2022-01-14"
study_reg_date = "2021-01-14"
study_end_date = "2022-01-21"

def create_valid_appointments():
    return (appointments.where((appointments.start_date) ==
                        (appointments.seen_date)))
    
def secondary_referral(interval_start, interval_end): 
    secondary_referral_count = (opa_cost.where(opa_cost
                    .referral_request_received_date
                    .is_on_or_between(interval_start, interval_end))
                    .count_for_patient())
    return secondary_referral_count

def follow_up(interval_start, interval_end):
    appointments.app_prev_week = (appointments.where(
                (appointments.start_date
                .is_on_or_between(interval_start - days(7), interval_start - days(1))) &
                (appointments.seen_date == appointments.start_date)
                ).exists_for_patient()
                )
    appointments.app_curr_week = (appointments.where(
                (appointments.start_date.is_on_or_between(interval_start, interval_end)) &
                (appointments.seen_date == appointments.start_date)
                ).exists_for_patient()
                )
    follow_up = (appointments.where(
                        appointments.app_prev_week & appointments.app_curr_week)
                        .exists_for_patient())
    return follow_up

def reason_for_app(interval_start, interval_end, reason, valid_appointments):
    event = (clinical_events.where((clinical_events
                                    .snomedct_code
                                    .is_in(reason))
                                    & (clinical_events
                                        .date
                                        .is_on_or_between(interval_start, interval_end))
                                        )
            )
    result = (event.where(event.date.is_in(valid_appointments.start_date))
                       .count_for_patient()
                )
    return result

def count_appointments_in_interval(interval_start, interval_end, valid_appointments, valid_only=True):
    """
    Counts the number of appointments during the interval.
    Args:
        valid_only: If True, only counts valid appointments.
    Returns:
        The count of appointments per patient.
    """
    if valid_only:
        chosen_appointments = valid_appointments
    else:
        chosen_appointments = appointments
    return chosen_appointments.where(
            chosen_appointments.start_date.is_on_or_between(interval_start, interval_end)
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
    analgesic_total = 0  # For aggregating analgesic subtypes

    for medication, codes in med_dict.items():
        if medication == "antidepressant_pres":
            # Use clinical_events for antidepressants
            measure_count = clinical_events.where(
                (clinical_events.snomedct_code.is_in(codes))
                & clinical_events.date.is_on_or_between(interval_start, interval_end)
            ).count_for_patient()
        else:
            # Use medications for other drugs
            measure_count = medications.where(
                (medications.dmd_code.is_in(codes))
                & medications.date.is_on_or_between(interval_start, interval_end)
            ).count_for_patient()

        measures[medication] = measure_count

        # If it's an analgesic subtype, add to the total and remove its subtype measure
        if medication.startswith('analgesic'):
            analgesic_total += measure_count
            del measures[medication]

    # Add the aggregated analgesic measure
    measures['analgesic_pres'] = analgesic_total

    return measures

