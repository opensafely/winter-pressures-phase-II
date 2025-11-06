from ehrql import codelist_from_csv

def create_codelist_dict(dic: dict) -> dict:
    '''
    Create a dicionary of codelists, so that queries can be run iteratively on
    groups of codelists that are subject to the same ehrQL query.
    Args:
        dic: dictionary where key = name, value = codelist csv path
    Returns:
        Dictionary where key = name, value = codelist
    '''
    for name in dic:
        dic[name] = codelist_from_csv(dic[name], 
                                                column = "code")
    return dic


# Demogragic codelists
ethnicity = codelist_from_csv(
    "codelists/opensafely-ethnicity-snomed-0removed.csv",
    column="code",
    category_column="Grouping_6",
)

# Online consult types codelist:
online_consult = codelist_from_csv("codelists/user-martinaf-online-consultations-snomed-v01.csv", column="code")

# Appointment reasons codelist:
app_reason_dict = {
    "ARI": "codelists/opensafely-acute-respiratory-illness-primary-care.csv", # not a good codelist - misses many pneumonia codes
    "pneum_broad": "codelists/bristol-pneumonia.csv", # pneumonia specific codelist to compensate for above
    "neurological_app": "codelists/ons-neurological-disorders.csv",
    "sick_notes_app": "codelists/opensafely-sick-notes-snomed.csv"
}
app_reason_dict = create_codelist_dict(app_reason_dict)

# Append additional appointment reasons with SNOMED codes (no codelists); more specific top- usgae codes 
app_reason_dict["back_pain"] = ['279039007', '161891005', '161894002', '278860009', '279040009']
# Top usage codes for chest infection, without indication viral or bacterial. Search terms: respiratory infection | respiratory tract infection.
# Pneumonia excluded for specificity to conditions which may not neccessairly trigger Abx
app_reason_dict["chest_inf"] = ['50417007', '54150009', '195742007', '54398005', '448739000']
# Top pneumonia specific codes
app_reason_dict["pneum"] = ['233604007', '385093006', '312342009', '425464007', '278516003']

indication_dict = {"back_pain_opioid": app_reason_dict["back_pain"], 
                   "chest_inf_abx": app_reason_dict["chest_inf"],
                   "pneum_abx": app_reason_dict["pneum"]}

# Medications codelists:
med_dict ={
    "antidepressant_pres":"codelists/bristol-antidepressants-snomedct.csv",
    "antibiotic_pres":"codelists/opensafely-antibacterials.csv",
    "opioid_nasal":"codelists/opensafely-opioid-containing-medicines-buccal-nasal-and-oromucosal-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_inhale":"codelists/opensafely-opioid-containing-medicines-inhalation-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_oral":"codelists/opensafely-opioid-containing-medicines-oral-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_parental":"codelists/opensafely-opioid-containing-medicines-parenteral-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_rectal":"codelists/opensafely-opioid-containing-medicines-rectal-excluding-drugs-for-substance-misuse-dmd.csv",
    "opioid_transdermal":"codelists/opensafely-opioid-containing-medicines-transdermal-excluding-drugs-for-substance-misuse-dmd.csv",
    "chest_abx": "codelists/user-arinat-chest-abx-dmd.csv"
}
med_dict = create_codelist_dict(med_dict)

prescription_dict = {"opioid_oral": med_dict["opioid_oral"], 
                     "chest_abx1": med_dict["chest_abx"], 
                     "chest_abx2": med_dict["chest_abx"]}

# Co-morbidity codelists:
comorbid_dict = {
    "chronic_resp": "codelists/nhsd-primary-care-domain-refsets-crdatrisk1_cod.csv",
    "copd": "codelists/nhsd-primary-care-domain-refsets-copd_cod.csv",
    "copd_res": "codelists/nhsd-primary-care-domain-refsets-copdres_cod.csv",
    "asthma": "codelists/nhsd-primary-care-domain-refsets-ast_cod.csv",
    "asthma_res": "codelists/nhsd-primary-care-domain-refsets-astres_cod.csv",
    "diabetes": "codelists/nhsd-primary-care-domain-refsets-dm_cod.csv",
    "diabetes_res": "codelists/nhsd-primary-care-domain-refsets-dmres_cod.csv",
    "htn": "codelists/nhsd-primary-care-domain-refsets-hyp_cod.csv",
    "htn_res": "codelists/nhsd-primary-care-domain-refsets-hypres_cod.csv",
    "immuno_sup": "codelists/nhsd-immunosupression-pcdcluster-snomed-ct.csv"
}
comorbid_dict = create_codelist_dict(comorbid_dict)

# SRO measures
sro_dict = {
    "sodium_test": "codelists/opensafely-sodium-tests-numerical-value.csv",
    "alt_test": "codelists/opensafely-alanine-aminotransferase-alt-tests.csv",
    "sys_bp_test": "codelists/opensafely-systolic-blood-pressure-qof.csv",
    "chol_test": "codelists/opensafely-cholesterol-tests.csv",
    "rbc_test": "codelists/opensafely-red-blood-cell-rbc-tests.csv",
    "hba1c_test": "codelists/opensafely-glycated-haemoglobin-hba1c-tests.csv",
    "cvd_10yr": "codelists/opensafely-cvd-risk-assessment-score-qof.csv",
    "thy_test": "codelists/opensafely-thyroid-stimulating-hormone-tsh-testing.csv",
    "asthma_review": "codelists/opensafely-asthma-annual-review-qof.csv",
    "copd_review": "codelists/opensafely-chronic-obstructive-pulmonary-disease-copd-review-qof.csv",
    "med_review1": "codelists/opensafely-care-planning-medication-review-simple-reference-set-nhs-digital.csv",
    "med_review2": "codelists/nhsd-primary-care-domain-refsets-medrvw_cod.csv"
}
sro_dict = create_codelist_dict(sro_dict)

# Combine medication review codelists into one codelist
sro_dict["med_review"] = sro_dict["med_review1"] + sro_dict["med_review2"]
del sro_dict["med_review1"]
del sro_dict["med_review2"]

# Seasonal respiratory illness
resp_dict = {
    "flu_specific": "codelists/opensafely-influenza-identification-primary-care.csv",
    "flu_sensitive": "codelists/opensafely-influenza-identification-primary-care-maximal-sensitivity.csv",
    "covid_specific": "codelists/opensafely-covid-19-identification-primary-care.csv",
    "rsv_specific": "codelists/opensafely-rsv-identification-primary-care.csv",
}
resp_dict = create_codelist_dict(resp_dict)

# Define sensitive codelists as additional codes not found in specific codelist
resp_dict["covid_sensitive"] = set(resp_dict["covid_specific"]) - set(codelist_from_csv("codelists/opensafely-covid-19-identification-primary-care-maximal-sensitivity.csv", column = "code"))
resp_dict["rsv_sensitive"] = set(resp_dict["rsv_specific"]) - set(codelist_from_csv("codelists/opensafely-rsv-identification-primary-care-maximal-sensitivity.csv", column = "code"))

# Supporting codelists for sensitive seasonal respiratory illnesses
fever_codelist = codelist_from_csv("codelists/opensafely-symptoms-fever.csv", column="code")
flu_med_codelist = codelist_from_csv("codelists/user-emprestige-influenza-identification-prescriptions-maximal-sensitivity-dmd.csv", column="dmd_id")
flu_sensitive_exclusion = codelist_from_csv("codelists/opensafely-influenza-exclusion-primary-care-maximal-sensitivity.csv", column="code")

covid_med_codelist = codelist_from_csv("codelists/opensafely-covid-19-identification-prescriptions.csv", column="code")
covid_sensitive_exclusion = codelist_from_csv("codelists/opensafely-covid-19-exclusion-primary-care-maximal-sensitivity.csv", column="code")

rsv_med_codelist = codelist_from_csv("codelists/opensafely-rsv-identification-prescriptions-maximal-sensitivity.csv", column="code")
rsv_sensitive_exclusion = codelist_from_csv("codelists/opensafely-rsv-exclusion-primary-care-maximal-sensitivity.csv", column="code")