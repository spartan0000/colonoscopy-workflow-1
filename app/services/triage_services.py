import openai
from openai import OpenAI, AzureOpenAI
import os
from typing import List
import json
from dotenv import load_dotenv
import yaml
from pathlib import Path

import asyncio
import requests

import random

from datetime import datetime

from app.clients.llm_clients import chat_client, hnz_client
from app.services.parsing.triage.colonoscopy_triage_model import ColonoscopySummary

load_dotenv()

BASE_PATH = Path(__file__).parent.parent
PROMPT_PATH = BASE_PATH / 'services' / 'parsing' / 'triage'
DATA_PATH = ""
   
def load_prompt(prompt_file:str) -> str:
    prompt_path = PROMPT_PATH / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error loading YAML file: {e}")
        system_prompt = f"{config['prompt']['content']}"
        rules = config['prompt'].get('rules')
        if rules:
            rules_text = "\n Rules: \n" + "\n".join(f'- {rule}' for rule in rules)
            system_prompt = f'{system_prompt}\n{rules_text}'
        pydantic_model = config.get('pydantic_model')
        if pydantic_model:
            system_prompt = f'{system_prompt}\n Please format the output according to this pydantic model: {pydantic_model}'
        return system_prompt



async def format_query_json(user_query: str) -> dict: 
    PROMPT_FILE = PROMPT_PATH/'extract_json.yaml'
    with open(PROMPT_FILE, 'r', encoding = 'utf-8') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise Exception(f'Error loading YAML prompt file: {e}')
        system_prompt = f"{config['prompt']['content']}"
        if 'rules' in config:
            rules_text = '\nRules:\n' + '\n'.join(f'- {rule}' for rule in config['rules'])
            system_prompt = f'{system_prompt}\n{rules_text}'
        
        

    user_prompt = f'Please format this medical text into structured JSON output - {user_query}'

    response1 = await chat_client.responses.parse(
        model = 'gpt-5-mini',
        
        input = [
            {
                'role':'system',
                'content': system_prompt,
            },
            {
                'role': 'user',
                'content': user_prompt,
            }
        ],
        text_format = ColonoscopySummary
        

    )

    output = response1.output_parsed.model_dump()
    return output

    # try:
    #     raw_output = response1.output_text
    #     result_json = json.loads(raw_output)
    #     return result_json
    # except json.JSONDecodeError:
    #     return {'error': 'Failed to parse JSON', 'raw_output': response1.output_text}
    
async def send_request(report_text: str, api_url: str):
    '''
    Sends a free text report to the API endpoint and returns a recommendation based on the report and database contents
    '''

    data = {'user_query': report_text}
    
    response = requests.post(api_url, json = data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'API request failed with status code {response.status_code}: {response.text}')



rules_dict = {
    'rule_1': 'Cecum not reached',
    'rule_2': 'Inadequate prep',
    'rule_3': 'Serrated polyposis syndrome',
    'rule_4': 'Greater than 10 adenomatous polyps',
    'rule_5': 'SSL >= 10mm',
    'rule_6': 'SSL with dysplasia',
    'rule_7': 'Adenoma >= 10mm',
    'rule_8': 'Tubulovillous or villous adenoma',
    'rule_9': 'Adenoma with HGD',
    'rule_10': '5 or more SSL all less than 10mm, no other polyps, no high risk features',
    'rule_11': '5-9 adenomas with no high risk features and no SSL',
    'rule_12': '5-9 combined adenomas and SSL',
    'rule_13': 'Hyperplastic polyp >= 10mm',
    'rule_14': '3-4 adenomas, no SSL, no high risk features',
    'rule_15': '1-4 SSL < 10mm no dysplasia no other polyps',
    'rule_16': 'Adenoma and SSL present, less than 5 total polyps, no high risk features',
    'rule_17': '1-2 adenomas less than 10mm no hgd',
    'rule_18': 'No polyps',
    'rule_19': 'No criteria met, needs human review',
    'rule_20': 'Patient aged out',
    'rule_21': 'Incomplete/piecemeal resection or incomplete retrieval',
    'rule_22': 'IBD',
    'rule_23': 'Discharged due to no polyps and family history category 1 or 2',
    'rule_24': 'No polyps but biopsies taken, needs human review'
}




def triage(data: dict):
    n_adenoma = 0
    max_adenoma = 0
    hgd_adenoma = False
    n_ssl = 0
    max_ssl = 0
    dysplastic_ssl = False
    n_hyperplastic = 0
    max_hyperplastic = 0
    biopsies_taken = False
    
    tva = False
    incomplete_resection = False
    incomplete_retrieval = False
    
    follow_up = None
    patient_age = data['patient_age']
    indication = data.get('indication', '')
    total_polyps = data['colonoscopy'][0]['number_of_polyps']
    cecum = data['colonoscopy'][0]['cecum_reached']
    bbps = data['colonoscopy'][0]['bostonBowelPrepScore']
    if data['colonoscopy'][0]['biopsies']:
        biopsies_taken = True
    if data['colonoscopy'][0]['polyps']:
        polyps = data['colonoscopy'][0]['polyps']
        for polyp in polyps:
            if polyp['type'] == 'adenoma':
                n_adenoma += 1
                max_adenoma = max(max_adenoma, polyp['size'])
                if polyp['dysplasia'] == 'high_grade':
                    hgd_adenoma = True
            elif polyp['type'] == 'sessile_serrated_polyp':
                n_ssl += 1
                max_ssl = max(max_ssl, polyp['size'])
                if polyp['dysplasia'] in ['low_grade', 'high_grade']:
                    dysplastic_ssl = True
            elif polyp['type'] == 'hyperplastic_polyp':
                n_hyperplastic += 1
                max_hyperplastic = max(max_hyperplastic, polyp['size'])
            elif polyp['type'] == 'tubulovillous_or_villous_adenoma':
                tva = True        
            if polyp['resection'] != 'complete':
                incomplete_resection = True
            if polyp['retrieval'] != 'complete':
                incomplete_retrieval = True

    #need human review - these all have a return statement so that no other criteria are triggered further down the line
    #for now, have follow up value of 0 represent needing human review
    if cecum == 'no':
        return {'follow_up': 0, 'rule': 'rule_1', 'reason': 'Cecum not reached'}
    elif bbps['total'] < 6 or bbps['right'] < 2 or bbps['transverse'] < 2 or bbps['left'] < 2:
        return {'follow_up': 0, 'rule': 'rule_2', 'reason':'Inadequate prep'}
    elif indication == 'sps': 
        return {'follow_up': 0, 'rule': 'rule_3', 'reason': 'Serrated polyposis syndrome'}
    #this seems like something a human should look at
    elif n_adenoma >= 10:
        return {'follow_up': 0, 'rule': 'rule_4', 'reason': 'Greater than 10 adenomatous polyps'}
    #incomplete resection or retrieval
    elif incomplete_resection == True or incomplete_retrieval == True:
        return {'follow_up': 0, 'rule': 'rule_21', 'reason': 'Incomplete/piecemeal resection or incomplete retrieval'}
    elif indication == 'ibd':
        return {'follow_up': 0, 'rule': 'rule_22', 'reason': 'IBD'}
    
    #biopsies taken - needs human review to determine why and what follow up is needed since biopsies alone aren't in the surveillance guidelines

    elif biopsies_taken == True:
        return {'follow_up': 0, 'rule': 'rule_24', 'reason': 'Biopsies taken, needs human review to determine reason and follow up'}
 
    #3 years
    ###These are high risk polyps - triaging rules vary somewhat for these regarding the age out criteria
    elif max_ssl >=10:
        return {'follow_up': 3, 'rule': 'rule_5', 'reason': 'SSL >= 10mm'}
    
    elif dysplastic_ssl == True:
        return {'follow_up': 3, 'rule': 'rule_6', 'reason': 'SSL with dysplasia'}
    
    elif max_adenoma >= 10:
        return {'follow_up': 3, 'rule': 'rule_7', 'reason': 'Adenoma >= 10mm'}
    elif tva == True:
        return {'follow_up': 3, 'rule': 'rule_8', 'reason': 'Tubulovillous or villous adenoma'}
    elif hgd_adenoma == True:
        return {'follow_up': 3, 'rule': 'rule_9', 'reason': 'Adenoma with HGD'}
    
    ###These are other indications for 3 year follow up
    elif n_adenoma == 0 and n_ssl >= 5 and max_ssl < 10:
        return {'follow_up': 3, 'rule': 'rule_10', 'reason': '5 or more SSL all less than 10mm, no other polyps, no high risk features'}
    elif n_ssl == 0 and 5 <= n_adenoma <= 9 and max_adenoma < 10 and hgd_adenoma == False:
        return {'follow_up': 3, 'rule': 'rule_11', 'reason': '5-9 adenomas with no high risk features and no SSL'}
    elif n_ssl > 0 and n_adenoma > 0 and 5 <= total_polyps <= 9:
        return {'follow_up': 3, 'rule': 'rule_12', 'reason': '5-9 combined adenomas and SSL'}
    elif max_hyperplastic >= 10:
        return {'follow_up': 3, 'rule': 'rule_13', 'reason': 'Hyperplastic polyp >= 10mm'}
    


    #5 years
    elif n_ssl == 0 and 3 <= n_adenoma <= 4 and max_adenoma < 10 and hgd_adenoma == False:
        return {'follow_up': 5, 'rule': 'rule_14', 'reason': '3-4 adenomas, no SSL, no high risk features'}
    
    elif 1 <= n_ssl <= 4 and max_ssl < 10 and n_adenoma == 0:
        return {'follow_up': 5, 'rule': 'rule_15', 'reason': '1-4 SSL < 10mm no dysplasia no other polyps'}
    
    elif n_ssl > 0 and total_polyps <= 4 and max_ssl < 10 and max_adenoma < 10:
        return {'follow_up': 5, 'rule': 'rule_16', 'reason': 'Adenoma and SSL present, less than 5 total polyps, no high risk features'}
    

    #10 years

    elif n_ssl == 0 and 0 < n_adenoma < 3 and max_adenoma < 10 and hgd_adenoma == False:
        return {'follow_up': 10, 'rule': 'rule_17', 'reason': '1-2 adenomas less than 10mm no hgd'}
    elif n_ssl == 0 and n_adenoma == 0: #no polyps - biopsies taken is covered by rule earlier in the function so this only gets triggered if no biopsies and also no polyps
        return {'follow_up': 10, 'rule': 'rule_18', 'reason': 'No polyps'}
    
    ###Add discharge criteria here?

    #if no polyps and family history category 1 or 2
    if not data['colonoscopy'][0]['polyps'] and indication in ['family_history_category_1', 'family_history_category_2']:
        return {'follow_up': 20, 'rule': 'rule_23', 'reason': 'Discharged due to no polyps and family history category 1 or 2'}
    

    
    #if no criteria met, refer for human review
    else:
        return {'follow_up': 0, 'rule': 'rule_19', 'reason': 'No criteria met, needs human review'}

def age_out(data: dict, outcome: dict):
    #see if the patient will age out
    patient_age = data['patient_age']
    follow_up = outcome['follow_up']
    rule = outcome['rule']
    if rule in ['rule_5', 'rule_6', 'rule_7', 'rule_8', 'rule_9'] and patient_age <= 75: #high risk polyps can rescope up to age 78
        return outcome
    elif follow_up is not None and follow_up != 0 and follow_up + patient_age > 75:
        return {'follow_up': 20, 'rule': 'rule_20', 'reason': 'Patient aged out'}
    
    else:
        return outcome



def triage_with_age_out(data, outcome):
    outcome = triage(data)
    return age_out(data, outcome)





async def main():
    with open(DATA_PATH / 'sample_patient_report_1.txt', 'r', encoding = 'utf-8') as f:
        report = f.read()
    data = await format_query_json(report)
    recommendation = triage(data)

    final = triage_with_age_out(data, recommendation)
    print(f'Given this data\n {data}\n\n The recommendation is: {final}')
    

if __name__ == '__main__':
    asyncio.run(main())