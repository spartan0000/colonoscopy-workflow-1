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
from app.services.parsing.triage.colonoscopy_triage_model import ColonoscopySummary, UserInput

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
    system_prompt = load_prompt('extract_json.yaml')
        

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

#input is the colonoscopy entry from the JSON output from the LLM
#helper function to get polyp data from the JSON output before going into the rules engine

def extract_polyp_data(colonoscopy_entry: dict) -> dict: #takes the output from LLM and normalizes it so that the triage function doesn't have to pull values
    stats = {
        'n_adenoma': 0,
        'max_adenoma': 0,
        'hgd_adenoma': False,
        'n_ssl': 0,
        'max_ssl': 0,
        'dysplastic_ssl': False,
        'n_hyperplastic': 0,
        'max_hyperplastic': 0,
        'biopsies_taken': bool(colonoscopy_entry.get('biopsies')),
        'tva': False,
        'incomplete_resection': True,
        'incomplete_retrieval': True,
        

    }
    
    for polyp in colonoscopy_entry.get('polyps', []):
        ptype = polyp.get('type')
        size = polyp.get('size', 0)
        dysplasia = polyp.get('dysplasia')
        if polyp.get('resection') == 'complete':
            stats['incomplete_resection'] = False #default value is True (incomplete resection) set above
        if polyp.get('retrieval') == 'complete':
            stats['incomplete_retrieval'] = False #default value is True (incomplete retrieval) set above



        if ptype == 'adenoma':
            stats['n_adenoma'] += 1
            stats['max_adenoma'] = max(stats['max_adenoma'], size)
            if dysplasia == 'high_grade':
                stats['hgd_adenoma'] = True
        elif ptype == 'sessile_serrated_polyp':
            stats['n_ssl'] += 1
            stats['max_ssl'] = max(stats['max_ssl'], size)
            if dysplasia in ['low_grade', 'high_grade']:
                stats['dysplastic_ssl'] = True
        elif ptype == 'hyperplastic_polyp':
            stats['n_hyperplastic'] += 1
            stats['max_hyperplastic'] = max(stats['max_hyperplastic'], size)
        elif ptype == 'tubulovillous_or_villous_adenoma':
            stats['tva'] = True
        return stats

def normalize_data(data: dict) -> dict: #normalize the data in the JSON output to make it easier to work with in the triage function
    colonoscopy_entry = data.get('colonoscopy', [{}])[0]
    stats = extract_polyp_data(colonoscopy_entry)

    normalized_data = {
        'patient_age': colonoscopy_entry.get('patient_age', 0),
        'indication': colonoscopy_entry.get('indication', ''),
        'bbps': colonoscopy_entry.get('bostonBowelPrepScore', 0),
        'cecum_reached': colonoscopy_entry.get('cecum_reached', 'no'),
        'total_polyps': colonoscopy_entry.get('number_of_polyps', 0),
        **stats
    }
    return normalized_data
 
def triage(data: dict):
    # colonoscopy_entry = data.get('colonoscopy', [{}])[0]
    # stats = extract_polyp_data(colonoscopy_entry)

    # n_adenoma = stats['n_adenoma']
    # max_adenoma = stats['max_adenoma']
    # hgd_adenoma = stats['hgd_adenoma']
    # n_ssl = stats['n_ssl']
    # max_ssl = stats['max_ssl']
    # dysplastic_ssl = stats['dysplastic_ssl']
    # n_hyperplastic = stats['n_hyperplastic']
    # max_hyperplastic = stats['max_hyperplastic']
    # biopsies_taken = stats['biopsies_taken']
    
    # tva = stats['tva']
    # incomplete_resection = stats['incomplete_resection']
    # incomplete_retrieval = stats['incomplete_retrieval']

    # bbps = colonoscopy_entry.get('bostonBowelPrepScore', None)
    # cecum = colonoscopy_entry.get('cecum_reached', None)
    # total_polyps = colonoscopy_entry.get('number_of_polyps', 0)
    
    # follow_up = None
    # patient_age = colonoscopy_entry.get('patient_age', 0)
    # indication = colonoscopy_entry.get('indication', '')



    

    #need human review - these all have a return statement so that no other criteria are triggered further down the line
    #for now, have follow up value of 0 represent needing human review
    if data['cecum_reached'] == 'no':
        return {'follow_up': 0, 'rule': 'rule_1', 'reason': 'Cecum not reached'}
    elif data['bbps']['total'] < 6 or data['bbps']['right'] < 2 or data['bbps']['transverse'] < 2 or data['bbps']['left'] < 2:
        return {'follow_up': 0, 'rule': 'rule_2', 'reason':'Inadequate prep'}
    elif data['indication'] == 'sps': 
        return {'follow_up': 0, 'rule': 'rule_3', 'reason': 'Serrated polyposis syndrome'}
    #this seems like something a human should look at
    elif data['n_adenoma'] >= 10:
        return {'follow_up': 0, 'rule': 'rule_4', 'reason': 'Greater than 10 adenomatous polyps'}
    #incomplete resection or retrieval
    elif data['incomplete_resection'] == True or data['incomplete_retrieval'] == True:
        return {'follow_up': 0, 'rule': 'rule_21', 'reason': 'Incomplete/piecemeal resection or incomplete retrieval'}
    elif data['indication'] == 'ibd':
        return {'follow_up': 0, 'rule': 'rule_22', 'reason': 'IBD'}
    
    #biopsies taken - needs human review to determine why and what follow up is needed since biopsies alone aren't in the surveillance guidelines

    elif data['biopsies_taken'] == True:
        return {'follow_up': 0, 'rule': 'rule_24', 'reason': 'Biopsies taken, needs human review to determine reason and follow up'}
 
    #3 years
    ###These are high risk polyps - triaging rules vary somewhat for these regarding the age out criteria
    elif data['max_ssl'] >=10:
        return {'follow_up': 3, 'rule': 'rule_5', 'reason': 'SSL >= 10mm'}
    
    elif data['dysplastic_ssl'] == True:
        return {'follow_up': 3, 'rule': 'rule_6', 'reason': 'SSL with dysplasia'}
    
    elif data['max_adenoma'] >= 10:
        return {'follow_up': 3, 'rule': 'rule_7', 'reason': 'Adenoma >= 10mm'}
    elif data['tva'] == True:
        return {'follow_up': 3, 'rule': 'rule_8', 'reason': 'Tubulovillous or villous adenoma'}
    elif data['hgd_adenoma'] == True:
        return {'follow_up': 3, 'rule': 'rule_9', 'reason': 'Adenoma with HGD'}
    
    ###These are other indications for 3 year follow up
    elif data['n_adenoma'] == 0 and data['n_ssl'] >= 5 and data['max_ssl'] < 10:
        return {'follow_up': 3, 'rule': 'rule_10', 'reason': '5 or more SSL all less than 10mm, no other polyps, no high risk features'}
    elif data['n_ssl'] == 0 and 5 <= data['n_adenoma'] <= 9 and data['max_adenoma'] < 10 and data['hgd_adenoma'] == False:
        return {'follow_up': 3, 'rule': 'rule_11', 'reason': '5-9 adenomas with no high risk features and no SSL'}
    elif data['n_ssl'] > 0 and data['n_adenoma'] > 0 and 5 <= data['total_polyps'] <= 9:
        return {'follow_up': 3, 'rule': 'rule_12', 'reason': '5-9 combined adenomas and SSL'}
    elif data['max_hyperplastic'] >= 10:
        return {'follow_up': 3, 'rule': 'rule_13', 'reason': 'Hyperplastic polyp >= 10mm'}
    


    #5 years
    elif data['n_ssl'] == 0 and 3 <= data['n_adenoma'] <= 4 and data['max_adenoma'] < 10 and data['hgd_adenoma'] == False:
        return {'follow_up': 5, 'rule': 'rule_14', 'reason': '3-4 adenomas, no SSL, no high risk features'}
    
    elif 1 <= data['n_ssl'] <= 4 and data['max_ssl'] < 10 and data['n_adenoma'] == 0:
        return {'follow_up': 5, 'rule': 'rule_15', 'reason': '1-4 SSL < 10mm no dysplasia no other polyps'}
    
    elif data['n_ssl'] > 0 and data['total_polyps'] <= 4 and data['max_ssl'] < 10 and data['max_adenoma'] < 10:
        return {'follow_up': 5, 'rule': 'rule_16', 'reason': 'Adenoma and SSL present, less than 5 total polyps, no high risk features'}
    

    #10 years

    elif data['n_ssl'] == 0 and 0 < data['n_adenoma'] < 3 and data['max_adenoma'] < 10 and data['hgd_adenoma'] == False:
        return {'follow_up': 10, 'rule': 'rule_17', 'reason': '1-2 adenomas less than 10mm no hgd'}
    elif data['n_ssl'] == 0 and data['n_adenoma'] == 0: #no polyps - biopsies taken is covered by rule earlier in the function so this only gets triggered if no biopsies and also no polyps
        return {'follow_up': 10, 'rule': 'rule_18', 'reason': 'No polyps'}
    
    ###Add discharge criteria here?

    #if no polyps and family history category 1 or 2
    if not data['polyps'] and data['indication'] in ['family_history_category_1', 'family_history_category_2']:
        return {'follow_up': 20, 'rule': 'rule_23', 'reason': 'Discharged due to no polyps and family history category 1 or 2'}
    

    
    #if no criteria met, refer for human review
    else:
        return {'follow_up': 0, 'rule': 'rule_19', 'reason': 'No criteria met, needs human review'}

def age_out(data: dict, outcome: dict): #takes the original input to the triage function as well as the output and checks if the patient would age out of screening based on the follow up recommendation and their current age
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


async def final_triage(data: UserInput):

    report = data.user_input
    json_data = await format_query_json(report)
    normalized_data = normalize_data(json_data)
    recommendation = triage(normalized_data)
    final = triage_with_age_out(normalized_data, recommendation)
    return final



async def main():
    with open(DATA_PATH / 'sample_patient_report_1.txt', 'r', encoding = 'utf-8') as f:
        report = f.read()
    data = await format_query_json(report)
    recommendation = triage(data)

    final = triage_with_age_out(data, recommendation)
    print(f'Given this data\n {data}\n\n The recommendation is: {final}')
    

if __name__ == '__main__':
    asyncio.run(main())