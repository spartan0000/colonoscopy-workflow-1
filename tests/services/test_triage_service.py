import pytest

from unittest.mock import AsyncMock, patch

from app.services.triage_services import triage, age_out, normalize_data, triage_with_age_out



#@patch('app.services.parsing.triage_services', new_callable=AsyncMock)

def test_normalize_data():
    input = {
        
        "colonoscopy": [{
            "polyps": [{
                "type": "adenoma",
                "size": 15,
                "dysplasia": "high_grade",
                "resection": "complete",
                "retrieval": "incomplete"
            }],
            "bostonBowelPrepScore": {
                "total": 7,
                "right": 2,
                "transverse": 3,
                "left": 2 
             },
             "patient_age": 60,
             "cecum_reached": 'yes',
             "biopsies_taken": False,
             "indication": "bleeding",
             
        }]
    }
    
    normalized_data = normalize_data(input)

    assert normalized_data['hgd_adenoma'] == True
    assert normalized_data['n_adenoma'] == 1
    assert normalized_data['max_adenoma'] == 15
    assert normalized_data['n_ssl'] == 0
    assert normalized_data['incomplete_resection'] == False
    assert normalized_data['incomplete_retrieval'] == True
    assert normalized_data['bbps']['total'] == 7
    assert normalized_data['bbps']['right'] == 2
    assert normalized_data['cecum_reached'] == 'yes'
    assert normalized_data['patient_age'] == 60
    assert normalized_data['indication'] == 'bleeding'

def test_normalized_data_as_input_and_large_adenoma():
    input = {
        
        "colonoscopy": [{
            "polyps": [{
                "type": "adenoma",
                "size": 15,
                "dysplasia": "high_grade",
                "resection": "complete", 
                "retrieval": "complete"
            }],
            "bostonBowelPrepScore": {
                "total": 7,
                "right": 2,
                "transverse": 3,
                "left": 2 
             },
             "patient_age": 60,
             "cecum_reached": 'yes',
             "biopsies_taken": False,
             "indication": "bleeding",
             
        }]
    }
    normalized_data = normalize_data(input)
    recommendation = triage(normalized_data)
    final = triage_with_age_out(normalized_data, recommendation)

    assert final['follow_up'] == 3

def test_age_out_with_normalized_data():
    input = {
        
        "colonoscopy": [{
            "polyps": [{
                "type": "adenoma",
                "size": 5,
                "dysplasia": "low_grade",
                "resection": "complete",
                "retrieval": "complete"
            },
            {"type": "adenoma",
             "size": 7,
             "dysplasia": "low_grade",
             "resection": "complete",
             "retrieval": "complete"
             }],
            "bostonBowelPrepScore": {
                "total": 7,
                "right": 2,
                "transverse": 3,
                "left": 2 
             },
             "patient_age": 70,
             "cecum_reached": 'yes',
             "biopsies_taken": False,
             "indication": "bleeding",
             
        }]
    }
    normalized_data = normalize_data(input)
    recommendation = triage(normalized_data)
    final = triage_with_age_out(normalized_data, recommendation)

    assert final['reason'] == 'Patient aged out'

### Tests for rules that trigger human review ###
def test_cecum_not_reached():
    input = {
        "polyps": [],
        "n_adenoma": 0,
        "cecum_reached": 'no',
    }

    recommendation = triage(input)
    assert recommendation['follow_up'] == 0
    assert recommendation['rule'] == 'rule_1'
    assert recommendation['reason'] == 'Cecum not reached'

def test_poor_prep():

    input = {
        "bbps" : {
            "total": 5,
            "right": 2,
            "transverse": 1,
            "left": 2
        },
        "polyps": [],
        "total_polyps": 0,
        "cecum_reached": True,
        "biopsies_taken": True,
        "indication": ""
    }
    result = triage(input)
    
    assert result['follow_up'] == 0
    assert result['rule'] == 'rule_2'
    assert result['reason'] == 'Inadequate prep'

def test_diagnosis_sps():
    input = {
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,
        },
        'indication': 'sps'
    }
    recommendation = triage(input)
    assert recommendation['follow_up'] == 0
    assert recommendation['rule'] == 'rule_3'
    assert recommendation['reason'] == 'Serrated polyposis syndrome'

def test_more_than_10_adenomas():
    input = {
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': '',
        'n_adenoma': 11
    }
    recommendation = triage(input)
    assert recommendation['follow_up'] == 0
    assert recommendation['rule'] == 'rule_4'
    assert recommendation['reason'] == 'Greater than 10 adenomatous polyps'

def test_incomplete_resection_and_retrieval():
    input = {
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': '',
        'n_adenoma': 1,
        'incomplete_resection': True,
        'incomplete_retrieval': True
    }
    recommendation = triage(input)
    assert recommendation['follow_up'] == 0
    assert recommendation['rule'] == 'rule_21'
    assert recommendation['reason'] == 'Incomplete/piecemeal resection or incomplete retrieval'

def test_indication_ibd():
    input = {
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': 'ibd',
        'n_adenoma': 1,
        'incomplete_resection': False,
        'incomplete_retrieval': False
    }
    recommendation = triage(input)
    assert recommendation['follow_up'] == 0
    assert recommendation['rule'] == 'rule_22'
    assert recommendation['reason'] == 'IBD'

def test_no_polyps_biopsy():
    input = {
        "polyps": [],
        "n_adenoma": 0,
        "n_ssl": 0,
        "total_polyps": 0,
        "cecum_reached": True,
        "biopsies_taken": True,
        "bbps": {
            "total": 9,
            "right": 3,
            "transverse": 3,
            "left": 3
        },
        "indication": "",
        "incomplete_resection": False,
        "incomplete_retrieval": False,
    }

    result = triage(input)

    assert result['follow_up'] == 0
    assert result['rule'] == 'rule_24'
    assert result['reason'] == 'Biopsies taken, needs human review to determine reason and follow up'

def test_large_ssl():
    input = input = {
        
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': '',
        'biopsies_taken': False,
        'n_adenoma': 1,
        'n_ssl': 1,
        'max_ssl': 14,
        'dysplastic_ssl': False,
        'incomplete_resection': False,
        'incomplete_retrieval': False
    }
    result = triage(input)
    assert result['follow_up'] == 3
    assert result['rule'] == 'rule_5'
    assert result['reason'] == 'SSL >= 10mm'


def test_ssl_with_dysplasia():
    input = {
        
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': '',
        'biopsies_taken': False,
        'n_adenoma': 1,
        'n_ssl': 1,
        'max_ssl': 5,
        'dysplastic_ssl': True,
        'incomplete_resection': False,
        'incomplete_retrieval': False
    }
    result = triage(input)
    assert result['follow_up'] == 3
    assert result['rule'] == 'rule_6'
    assert result['reason'] == 'SSL with dysplasia'

def test_tva():
    input = {
        
        'cecum_reached': 'yes',
        'bbps': {
            'total': 9,
            'right': 3,
            'transverse': 3,
            'left': 3,

        },
        'indication': '',
        'biopsies_taken': False,
        'n_adenoma': 1,
        'max_adenoma': 5,
        'n_ssl': 0,
        'max_ssl': 0,
        'dysplastic_ssl': False,
        'incomplete_resection': False,
        'incomplete_retrieval': False,
        'tva': True
    }
    result = triage(input)
    assert result['follow_up'] == 3
    assert result['rule'] == 'rule_8'
    assert result['reason'] == 'Tubulovillous or villous adenoma'
