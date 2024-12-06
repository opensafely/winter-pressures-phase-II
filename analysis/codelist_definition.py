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
    "flu_app": "codelists/opensafely-acute-respiratory-illness-primary-care.csv",
    "neurological_app": "codelists/ons-neurological-disorders.csv",
    "sick_notes_app": "codelists/opensafely-sick-notes-snomed.csv"
}
app_reason_dict = create_codelist_dict(app_reason_dict)

# Medications codelists:
med_dict ={
    "antidepressant_pres":"codelists/bristol-antidepressants-snomedct.csv",
    "antibiotic_pres":"codelists/opensafely-antibacterials.csv",
    "analgesic_nasal":"codelists/opensafely-opioid-containing-medicines-buccal-nasal-and-oromucosal-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_inhale":"codelists/opensafely-opioid-containing-medicines-inhalation-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_oral":"codelists/opensafely-opioid-containing-medicines-oral-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_parental":"codelists/opensafely-opioid-containing-medicines-parenteral-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_rectal":"codelists/opensafely-opioid-containing-medicines-rectal-excluding-drugs-for-substance-misuse-dmd.csv",
    "analgesic_transdermal":"codelists/opensafely-opioid-containing-medicines-transdermal-excluding-drugs-for-substance-misuse-dmd.csv",
}
med_dict = create_codelist_dict(med_dict)

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