# This script is used to test the measures definition.

from datetime import date
from dataset import dataset

test_data = {
    # Expected in population with matching medication
    1: { 
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        # 1 pneumonia appointment matching a valid appointment date, 1 is not so shouldn't be included
        "clinical_events": [{"date": date(2022, 1, 15), "snomedct_code": "10625031000119102"}, 
                            {"date": date(2022, 1, 14), "snomedct_code": "10625031000119102"}, 
                            {"date": date(2022, 1, 15), "snomedct_code": "10625031000119102"}, 
                            {"date": date(2022, 1, 15), "snomedct_code": "24671000000101"}], # call from GP
        "addresses": [{"start_date": date(2010, 1, 1),"imd_rounded": 200}],
        # 1 outpatient appointment during interval, 1 after
        "opa_cost": [{"referral_request_received_date": date(2022, 1, 15)}, 
                     {"referral_request_received_date": date(2022, 1, 1)}],
        "practice_registrations": [{"start_date": date(2010, 1, 1), "end_date": date(2025, 1, 1), "practice_nuts1_region_name": "West Midlands"}],
        # 1 appointment before interval, 1 valid inside interval. 2 cancelled status (1 inside interval), 1 waiting status
        "appointments": [{"start_date": date(2022, 1, 8), "seen_date": date(2022, 1, 8), "status": "Cancelled by Unit"}, 
                         {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15), "status": "Waiting"}, 
                         {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15), "status": "Cancelled by Unit"}],
        # 1 flu vaccination, 1 covid vaccination, both in interval
        "vaccinations": [{"date": date(2022, 1, 15), "target_disease": "INFLUENZA"}, 
                         {"date": date(2022, 1, 15), "target_disease": "SARS-2 CORONAVIRUS"}],
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
    2: { # Expect follow up app = 0
        "patients": {"date_of_birth": date(1950, 1, 1), "sex": "male"},
        "medications": [],
        "clinical_events": [],
        "addresses": [{"start_date": date(2010, 1, 1),"imd_rounded": 200}],
        "opa_cost": [],
        "practice_registrations": [{"start_date": date(2010, 1, 1), "end_date": date(2025, 1, 1), "practice_nuts1_region_name": "West Midlands"}],
        "appointments": [{"start_date": date(2022, 1, 1), "seen_date": date(2022, 1, 1)}, {"start_date": date(2022, 1, 15), "seen_date": date(2022, 1, 15)}],
        "vaccinations": [],
        "emergency_care_attendances": [],
        "expected_in_population": True,
        "expected_columns": {
          "follow_up_app": False, # Because first appointment occurs 2 weeks rather than 1 week before
          "seen_in_interval": 1 
        },
    },
}
