from ehrql import case, codelist_from_csv, create_dataset, days, weeks, months, years, when, INTERVAL, create_measures, claim_permissions
from ehrql.tables.core import medications, patients
from ehrql.tables.tpp import (
    addresses,
    opa_cost,
    clinical_events,
    practice_registrations,
    appointments,
    vaccinations
)
import argparse

claim_permissions("appointments")

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=100)
measures.configure_disclosure_control(enabled=False)
parser = argparse.ArgumentParser()
parser.add_argument("--start_intv", help="Start date for the analysis")
args = parser.parse_args()
start_intv = args.start_intv

# Registered throughout the interval period (vs at the begining)
was_registered = practice_registrations.spanning(INTERVAL.start_date, INTERVAL.end_date).exists_for_patient()

# Extract events where start_date is within the time window
numerators = {}
numerators['start_exists'] = appointments.where(appointments
                                    .start_date
                                    .is_during(INTERVAL)
                                    )
numerators['seen_exists'] = appointments.where(appointments
                                    .seen_date
                                    .is_during(INTERVAL)
                                    )

# Defining measures, which are explained in more detail here: 
# https://docs.google.com/document/d/1EiJ3HJ4NqZZBkK8pv0-RqenCUkrhf6KzqaoqlYTwKqY/edit
statuses = ['Booked', 'Arrived', 'Did Not Attend', 'In Progress', 'Finished',
 'Requested', 'Blocked', 'Visit', 'Waiting', 'Cancelled by Patient','Cancelled by Unit',
  'Cancelled by Other Service', 'No Access Visit', 'Cancelled Due To Death', 'Patient Walked Out']
numerators['start_seen_same_interval'] = numerators['start_exists'].where((appointments
                                                               .seen_date
                                                               .is_during(INTERVAL)))
numerators['start_seen_same_day'] = (numerators['start_exists'].where(
                                            (appointments.start_date) ==
                                            (appointments.seen_date)
                                             )
                                    )
numerators['start_seen_same_week'] = numerators['start_exists'].where((appointments
                                             .seen_date
                                             .is_on_or_between((appointments.start_date + days (1)), (appointments.start_date + days(7))))
                                             )
numerators['start_seen_same_month'] = numerators['start_exists'].where((appointments
                                              .seen_date
                                              .is_on_or_between((appointments.start_date + days(1)), (appointments.start_date + months (1))))
                                             )
numerators['no_status'] = numerators['start_exists'].where(numerators['start_exists']
                                             .status
                                             .is_not_in(statuses))
numerators['null_status'] = numerators['start_exists'].where(numerators['start_exists']
                                             .status
                                             .is_null())
numerators['null_start'] = numerators['seen_exists'].where(numerators['seen_exists']
                                                 .start_date
                                                 .is_null())
numerators['null_seen'] = numerators['start_exists'].where(numerators['start_exists']
                                                 .seen_date
                                                 .is_null())
numerators['booked_no_start'] = (appointments.where((appointments.
                                                     booked_date.
                                                     is_during(INTERVAL)) & 
                                                     (appointments.
                                                      start_date.
                                                      is_null())))
numerators['proxy_null_start'] = numerators['seen_exists'].except_where((numerators['seen_exists']
                                                 .start_date
                                                 .is_on_or_between("2001-01-01", "2025-01-01")) |
                                                 (numerators['seen_exists']
                                                  .start_date
                                                  .is_null())
                                                 )
numerators['proxy_null_seen'] = numerators['start_exists'].except_where((numerators['start_exists']
                                                 .seen_date
                                                 .is_on_or_between("2001-01-01", "2025-01-01")) |
                                                 (numerators['start_exists']
                                                 .seen_date
                                                 .is_null())
                                                 )

# Creating status-specific measures
for numerator in list(numerators.keys()):
    for status in statuses:
        # Change name of measure to remove whitespace
        numerators[f"{numerator}_{status.replace(' ','')}"] = numerators[numerator].where(numerators[numerator]
                                        .status
                                        .is_in([status])
                                        )

# Defining measures ---
measures.define_defaults(
    denominator= was_registered,
    intervals=months(1).starting_on(start_intv),
)

# Adding measures
for numerator in numerators.keys():
    measures.define_measure(
        name=numerator,
        numerator=numerators[numerator].count_for_patient(),
    )
