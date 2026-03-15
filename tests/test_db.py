import pytest
from tests.conftest import TestingSessionLocal, test_engine
from sqlalchemy import text, inspect
from unittest.mock import patch, AsyncMock
from app.db.models.case import SampleTestCase, SamplePatient, SampleProcedure, SampleTriage


import app

inspector = inspect(test_engine)
print(f'TABLES: {inspector.get_table_names()}')

###need a test to test the histology matching to the correct patient - the join logic
#@pytest.mark.integration
#def test_histology_matching():

def test_db_connection():
    db = TestingSessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()

def test_db_insert(db_session): #uses sample test case - need to switch schema out later
    
    case = SampleTestCase(report_text="test report")
    db_session.add(case)
    db_session.commit()
    print(inspector.get_table_names())

    assert db_session.query(SampleTestCase).count() == 1

def test_triage_with_db_insert(client, db_session): #uses sample test case - need to switch schema out later
    input_data = {
        
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
        'hgd_adenoma': True,
        'n_ssl': 0,
        'max_ssl': 0,
        'dysplastic_ssl': False,
        'incomplete_resection': False,
        'incomplete_retrieval': False,
        'tva': False
    }
    
    with patch('app.services.triage_services.final_triage', new_callable=AsyncMock) as mock_final_triage:
        mock_final_triage.return_value = {"normalized_data":"some data",
                                          'recommendation': '3 years'}    
        response = client.post("/triage", json={'report_text': 'some_value'})
        assert response.status_code == 200

        #check if the result was added to the db

        from app.db.models.case import SampleTriage
        test_case = db_session.query(SampleTriage).order_by(SampleTriage.triage_id.desc()).first()
        assert test_case is not None
        
def test_triage_write_database(db_session): #uses sample test case - need to switch schema out later
    patient = SamplePatient(name="test patient", nhi='abc1234')
    db_session.add(patient)
    db_session.commit()

    procedure = SampleProcedure(patient_id = patient.patient_id, date = "2025-01-01T00:00:00")
    db_session.add(procedure)
    db_session.commit()

    triage_row = SampleTriage(procedure_id = procedure.procedure_id, raw_report = "some text blah blah blah", normalized_data = {'some': 'data'}, final_recommendation = {'follow_up': '1'})

    db_session.add(triage_row)
    db_session.commit()

    result = db_session.query(SampleTriage).filter_by(procedure_id=procedure.procedure_id).one()
    assert result.final_recommendation['follow_up'] == '1'