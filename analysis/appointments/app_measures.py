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

# Instantiate measures, with small number suppression turned off
measures = create_measures()
measures.configure_dummy_data(population_size=100)
measures.configure_disclosure_control(enabled=False)

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

# Flags
numerators['missing_seen'] = numerators['start_exists'].where(
                    (numerators['start_exists']
                     .seen_date
                     .is_before(INTERVAL.start_date)
                     ) |
                     (numerators['start_exists']
                      .seen_date
                      .is_after(INTERVAL.end_date)
                      )
                     )
numerators['missing_start'] = numerators['seen_exists'].where(
                    (numerators['seen_exists']
                     .start_date
                     .is_before(INTERVAL.start_date)
                     ) |
                     (numerators['seen_exists']
                      .start_date
                      .is_after(INTERVAL.end_date)
                      )
                     )
numerators['missing_seen_cancelled'] = numerators['start_exists'].where(numerators['start_exists']
                                                 .status
                                                 .is_in(['Did Not Attend', 'Blocked', 
                                                         'Cancelled by Patient', 'Cancelled by Unit', 
                                                         'Cancelled by Other Service', 'Cancelled Due To Death']
                                                         )
                                                )

# Defining measures ---
measures.define_defaults(
    denominator= was_registered,
    intervals=weeks(6).starting_on("2022-01-03"),
)
# Adding measures
for numerator in numerators.keys():
    measures.define_measure(
        name=numerator,
        numerator=numerators[numerator].count_for_patient(),
    )