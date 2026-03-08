import pytest
from tests.conftest import TestingSessionLocal
from sqlalchemy import text
from unittest.mock import patch, AsyncMock
from app.db.models.case import SampleTestCase

import app


def test_db_connection():
    db = TestingSessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()

def test_db_insert(db_session):
    
    case = SampleTestCase(report_text="test report")
    db_session.add(case)
    db_session.commit()
    assert db_session.query(SampleTestCase).count() == 1

def test_triage_with_db_insert(client, db_session):
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
    with patch('app.services.triage_services.format_query_json', new_callable=AsyncMock) as mock_format_query_json,\
        patch('app.services.triage_services.normalize_data') as mock_normalize_data,\
        patch('app.services.triage_services.triage') as mock_triage,\
        patch('app.services.triage_services.triage_with_age_out') as mock_age_out:
        
        mock_format_query_json.return_value = {}
        mock_normalize_data.return_value = input_data
        mock_triage.return_value = {"follow_up": "3 years"}
        mock_age_out.return_value = {"follow_up": "3 years"}

        
        response = client.post("/triage", json={'report_text': 'some_value'})
        assert response.status_code == 200

        #check if the result was added to the db

        from app.db.models.case import SampleTestCase
        test_case = db_session.query(SampleTestCase).order_by(SampleTestCase.id.desc()).first()
        assert test_case is not None
        

