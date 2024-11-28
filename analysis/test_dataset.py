from datetime import date
from dataset import dataset

test_data = {
    # Expected in population with matching medication
    1: { #Expect follow up app = 1
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [],
        "medications": [],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1),"imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [{"start_date": date(2010, 1, 1), "end_date": date(2025, 1, 1), "practice_nuts1_region_name": "West Midlands"}],
        "appointments": [{"start_date": date(2022, 1, 8), "seen_date": date(2022, 1, 8)}, {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)}],
        "vaccinations": [],
        "expected_in_population": True,
        "expected_columns": {
            "follow_up_app": True,
            "appointments_in_interval": 1,
        },
    },
    2: { # Expect follow up app = 0
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [],
        "medications": [],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1),"imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [{"start_date": date(2010, 1, 1), "end_date": date(2025, 1, 1), "practice_nuts1_region_name": "West Midlands"}],
        "appointments": [{"start_date": date(2022, 1, 1), "seen_date": date(2022, 1, 1)}, {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)}],
        "vaccinations": [],
        "expected_in_population": True,
        "expected_columns": {
          "follow_up_app": False, # Because first appointment occurs 2 weeks rather than 1 week before
          "appointments_in_interval": 1 
        },
    },
}
