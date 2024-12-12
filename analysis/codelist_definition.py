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
    "codelists/opensafely-ethnicity.csv",
    column="Code",
    category_column="Grouping_6",
)

# Appointment reasons codelist:
app_reason_dict = {
    "resp_ill": "codelists/opensafely-acute-respiratory-illness-primary-care.csv", # not a good codelist - misses many pneumonia codes
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
    "depres": "codelists/nhsd-primary-care-domain-refsets-depr_cod.csv",
    "depres_res": "codelists/nhsd-primary-care-domain-refsets-depres_cod.csv",
    "mental_health": "codelists/qcovid-has_severe_mental_illness.csv",
    "neuro": "codelists/primis-covid19-vacc-uptake-cns_cov.csv",
    "immuno_sup": "codelists/nhsd-immunosupression-pcdcluster-snomed-ct.csv"
}
comorbid_dict = create_codelist_dict(comorbid_dict)