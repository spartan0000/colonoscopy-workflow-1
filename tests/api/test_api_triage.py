from fastapi.testclient import TestClient
from app.main import app
import pytest

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

    