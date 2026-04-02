from openai import OpenAI, AzureOpenAI, AsyncAzureOpenAI
import os

from dotenv import load_dotenv
import asyncio

from pathlib import Path
import yaml
import json

from fastapi import UploadFile
from io import BytesIO

load_dotenv()

from app.clients.llm_clients import transcribe_client, whisper_client, hnz_client, chat_client
from app.services.transcribe.colonoscopy_transcription_model import ColonoscopyReport # - this model needs to be updated to include more relevant data such as prep quality

BASE_PATH = Path(__file__).parent
PROMPT_PATH = BASE_PATH / 'transcribe'


#loads prompts
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
        return system_prompt


async def get_transcription_timestamps(upload_file: UploadFile) -> dict:
    
    
    timestamps = await whisper_client.audio.transcriptions.create(
        model = 'whisper',
        file = (upload_file.filename, upload_file.file, upload_file.content_type),
        response_format = 'verbose_json',
        timestamp_granularities = ['segment'],

    )

    #get rid of unnecessary data like tokens and logprobs
    clean_data = {
        'entire_text':timestamps.text,
        'segments': [
    {
        'start': seg.start,
        'end':seg.end,
        'text': seg.text
    }
        for seg in timestamps.segments
        ]
    }
    return clean_data


#cleaned data (dictionary) then goes into this function to extract polyp data and other endoscopy data in structured format
async def extract_json(user_input: dict) -> dict:
    prompt = load_prompt('extraction_prompt.yaml')
    
    transcript_text = f"""
    full text: {user_input['entire_text']}
    segments: {json.dumps(user_input['segments'], indent = 2)}
    """

    response = await chat_client.responses.parse(
        model = "gpt-5-mini",
        input = [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': transcript_text}
        ],
        text_format = ColonoscopyReport,
    )

    output = response.output_parsed.model_dump()
    return output

#then into this function to generate a final report in PDF
def convert_to_report(data: dict) -> str:
    pass


if __name__ == "__main__":
    pass