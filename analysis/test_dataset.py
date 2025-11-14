# This script is used to test the measures definition.

from datetime import date
from dataset import dataset

test_data = {
    # Expected in population with matching medication
    1: {
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        # 1 pneumonia appointment matching a valid appointment date, 1 is not so shouldn't be included
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "10625031000119102"},
            {"date": date(2022, 1, 14), "snomedct_code": "10625031000119102"},
            {"date": date(2022, 1, 15), "snomedct_code": "10625031000119102"},
            {"date": date(2022, 1, 15), "snomedct_code": "24671000000101"},
        ],  # call from GP
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        # 1 outpatient appointment during interval, 1 after
        "opa_cost": [
            {"referral_request_received_date": date(2022, 1, 15)},
            {"referral_request_received_date": date(2022, 1, 1)},
        ],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        # 1 appointment before interval, 1 valid inside interval. 2 cancelled status (1 inside interval), 1 waiting status
        "appointments": [
            {
                "start_date": date(2022, 1, 8),
                "seen_date": date(2022, 1, 8),
                "status": "Cancelled by Unit",
            },
            {
                "start_date": date(2022, 1, 15),
                "seen_date": date(2022, 1, 15),
                "status": "Waiting",
            },
            {
                "start_date": date(2022, 1, 15),
                "seen_date": date(2022, 1, 15),
                "status": "Cancelled by Unit",
            },
        ],
        # 1 flu vaccination, 1 covid vaccination, both in interval
        "vaccinations": [
            {"date": date(2022, 1, 15), "target_disease": "INFLUENZA"},
            {"date": date(2022, 1, 15), "target_disease": "SARS-2 CORONAVIRUS"},
        ],
        "emergency_care_attendances": [{"id": 1, "arrival_date": date(2022, 1, 15)}],
        "expected_in_population": True,
        "expected_columns": {
            "follow_up_app": True,
            "seen_in_interval": 2,
            "start_in_interval": 2,
            "vax_app": 2,
            "vax_app_covid": 1,
            "vax_app_flu": 1,
            "cancelled_app": 1,
            "waiting_app": 1,
            "secondary_referral": 1,
            "call_from_gp": 1,
            "emergency_care": 1,
        },
    },
    2: {  # Expect follow up app = 0
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [
            {"start_date": date(2022, 1, 1), "seen_date": date(2022, 1, 1)},
            {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)},
        ],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            # "follow_up_app": False, # Because first appointment occurs 2 weeks rather than 1 week before
            "seen_in_interval": 1
        },
    },  # -------------- Seasonal illnesses ---------------------------
    # Flu
    3: {  # Max sensitive flu - Max sensitivity event
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1001341000000106"}
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 1,
        },
    },
    4: {  # Max sensitive flu - Fever, then ARI a week later
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "10151000132103"},  # fever
            {"date": date(2022, 1, 25), "snomedct_code": "10509002"},
        ],  # ari
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 1,
        },
    },
    5: {  # Max sensitive flu - ARI, then fever a week later
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "10509002"},  # ari
            {"date": date(2022, 1, 25), "snomedct_code": "10151000132103"},
        ],  # fever
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 1,
        },
    },
    6: {  # No Max sensitive flu - Fever, but no ARI a week later
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "10151000132103"}
        ],  # fever
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 0,
        },
    },
    7: {  # Max sensitive flu - Flu antiviral
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [{"date": date(2022, 1, 15), "dmd_code": "36151011000001106"}],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 1,
        },
    },
    8: {  # No Max sensitive flu - Max sens event AND exclusion code in episode
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1001341000000106"},
            {"date": date(2022, 1, 3), "snomedct_code": "1002141000000100"},
        ],  # exclusion code
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 0,
        },
    },
    9: {  # Max sensitive flu - Max spec event AND exclusion code in episode
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1033051000000101"},
            {"date": date(2022, 1, 3), "snomedct_code": "1002141000000100"},
        ],  # exclusion code
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "flu_sensitive": 1,
        },
    },
    10: {  # No Max sensitive RSV - Only one rsv event
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "102496004"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "rsv_sensitive": 0,
        },
    },
    11: {  # Max sensitive RSV - 2 RSV events in episode
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "102496004"},
            {"date": date(2022, 1, 9), "snomedct_code": "103001002"},
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "rsv_sensitive": 1,
        },
    },
    12: {  # Max sensitive RSV - 1 RSV event later
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [{"date": date(2022, 1, 22), "snomedct_code": "103001002"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "rsv_sensitive": 0,
        },
    },
    13: {  # Max sensitive RSV - 1 RSV event + 1 prescription
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [{"date": date(2022, 1, 15), "dmd_code": "41953711000001109"}],
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "103001002"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "rsv_sensitive": 1,
        },
    },
    14: {  # No Max sensitive RSV - 1 prescription alone
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [{"date": date(2022, 1, 1), "dmd_code": "41953711000001109"}],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "rsv_sensitive": 0,
        },
    },
    15: {  # Overall resp: rsv case
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "102496004"},
            {"date": date(2022, 1, 22), "snomedct_code": "103001002"},
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"rsv_sensitive": 1, "overall_resp_sensitive": 1},
    },
    16: {  # Overall resp: unidentified case
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "102453009"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"overall_resp_sensitive": 1},
    },
    17: {  # No overall resp: unidentified case + exclusion
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "102453009"},
            {"date": date(2022, 1, 22), "snomedct_code": "1005131000000102"},
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"overall_resp_sensitive": 0},
    },
    18: {  # No flu due to no same day appt
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1001341000000106"}
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"flu_sensitive_with_appt": 0},
    },
    19: {  # Flu with same day appt
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1001341000000106"}
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [
            {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)}
        ],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"flu_sensitive_with_appt": 1},
    },
    20: {  # No Overall resp as no same day appt
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "102453009"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"overall_resp_sensitive_with_appt": 0},
    },
    21: {  # Overall resp with same day appt
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "102453009"}],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [
            {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)}
        ],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"overall_resp_sensitive_with_appt": 1},
    },
    22: {  # Sro prioritized
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "270442000"}
        ],  # asthma review
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "sro_prioritized": 1,
            "sro_deprioritized": 0,
            "asthma_review": 1,
        },
    },
    23: {  # Sro de-prioritized
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1013211000000103"}
        ],  # alt
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
            "sro_prioritized": 1,
            "sro_deprioritized": 0,
            "alt_test": 1,
        },
    },
    24: {  # 2 Sick notes - 3 events but 2 appts linking them
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [
            {"date": date(2022, 1, 15), "snomedct_code": "1321000000100"},
            {"date": date(2022, 1, 15), "snomedct_code": "1331000000103"},
            {"date": date(2022, 1, 15), "snomedct_code": "1341000000107"},
        ],
        "addresses": [{"start_date": date(2010, 1, 1), "imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [
            {
                "start_date": date(2010, 1, 1),
                "end_date": date(2025, 1, 1),
                "practice_nuts1_region_name": "West Midlands",
            }
        ],
        "appointments": [
            {
                "start_date": date(2022, 1, 15),
                "seen_date": date(2022, 1, 15),
            },
            {
                "start_date": date(2022, 1, 17),
                "seen_date": date(2022, 1, 17),
            },
        ],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {"sick_notes_app": 2},
    },
}
