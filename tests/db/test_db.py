import pytest
from app.db.session import SessionLocal
from sqlalchemy import text

def test_db_connection():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()

def test_triage_with_db_insert(client, db_session):
        input_data = {'report_text': 'patient had a colonoscopy'}
        response = client.post("/triage", json=input_data)
        assert response.status_code == 200

        #check if the result was added to the db

        from app.db.models.case import SampleTestCase
        test_case = db_session.query(SampleTestCase).order_by(SampleTestCase.id.desc()).first()
        assert test_case is not None
        assert test_case.report_text == 'patient had a colonoscopy'


