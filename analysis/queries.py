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
