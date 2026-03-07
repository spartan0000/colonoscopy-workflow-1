from fastapi.testclient import TestClient
from app.main import app
import pytest
from unittest.mock import AsyncMock, patch

client = TestClient(app)


##### Not a mocked test.  This hits the actual openai endpoint.  Use for integration testing only.
@pytest.mark.integration
def test_triage_endpoint(): 
    input = {'report_text':
             "Patient is a 60-year-old with a history of lower GI bleeding. During the colonoscopy, a 5mm adenoma was found in the ascending colon and was completely resected, but retrieval was incomplete. The Boston Bowel Prep Score was 7 (right: 2, transverse: 3, left: 2), and the cecum was reached. The indication for the colonoscopy was rectal bleeding."}
    
        
    response = client.post("/triage", json=input)
    print(response.json())
    assert response.status_code == 200

##############################   


def test_empty_input():
    response = client.post("/triage", json={})
    assert response.status_code == 422 #unprocessable entry due to validation error

def test_invalid_input():
    response = client.post("/triage", json={'report_text': 123}) #report text should be a string, not an integer
    assert response.status_code == 422 #unprocessable entry due to validation error

def test_missing_text():
    response = client.post("/triage", json={'report_text': ''}) #report text is empty
    assert response.status_code == 422 #unprocessable entry due to empty string validation error

def test_triage_response():
    with patch('app.services.triage_services.format_query_json', new_callable=AsyncMock) as mock_format_query_json,\
        patch('app.services.triage_services.normalize_data') as mock_normalize_data,\
        patch('app.services.triage_services.triage') as mock_triage,\
        patch('app.services.triage_services.triage_with_age_out') as mock_age_out:
        
        mock_format_query_json.return_value = {"formatted_data": "some formatted data"}
        mock_normalize_data.return_value = {"normalized_data": "some normalized data"}
        mock_triage.return_value = {"triage_result": "some triage result"}
        mock_age_out.return_value = {"age_out": "some age out result"}

        
        input = {"report_text": "patient had a colonoscopy"}

        response = client.post("/triage", json=input)
        print(response.status_code)
        print(response.json())
        assert response.status_code == 200
        assert response.json()['age_out'] == "some age out result"