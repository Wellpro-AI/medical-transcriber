# app/medical.py
import os
import json
import logging
import sys
import asyncio
from google.cloud import aiplatform,secretmanager
from vertexai.preview.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)
system_prompt_soap=""
system_prompt_medical=""
def access_secret_version(secret_id, version_id="latest"):
    """Access the payload for the given secret version if one exists."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
try:
    system_prompt_soap = access_secret_version("system_prompt_soap")
    system_prompt_medical = access_secret_version("system_prompt_medical")
except Exception as e:
    logger.error(f"Error reading system prompts: {e}")
    sys.exit(1)
async def extract_detailed_medical_data(conversation_context: str) -> str:
    """
    Extracts structured medical information from conversation text using Gemini.
    """
    try:
        aiplatform.init(project=os.getenv("PROJECTID"), location=os.getenv("LOCATION"))
        model = GenerativeModel("gemini-2.0-flash-001")
        system_prompt = system_prompt_medical   
        user_prompt = f"Conversation:\n{conversation_context}"
        logger.info(f"Extracting medical data from: {conversation_context}")
        response = model.generate_content(
            [Part.from_text(system_prompt), Part.from_text(user_prompt)],
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        content_result = response.candidates[0].content.text
        return content_result
    except json.JSONDecodeError:
        logger.error("Failed to parse Gemini response")
        return '"error": "Invalid JSON from AI model"'
    except Exception as e:
        logger.error(f"Medical extraction error: {e}")
        return '"error": "Medical data extraction failed"'

async def create_soap_note(text: str,notes:str) -> str:
    """
    Generates a SOAP note from the provided text using Gemini.
    """
    try:
        aiplatform.init(project=os.getenv("PROJECTID"), location=os.getenv("LOCATION"))
        model = GenerativeModel("gemini-2.0-flash-001")

    except Exception as e:
        logger.error(f"Error initializing Gemini in create_soap_note: {e}")


    try:
        user_prompt = f"Generate a detailed SOAP note for the following text:\n\n{text}"
        logger.info(f"Creating SOAP note for text: {text}")
        response = model.generate_content(
            [Part.from_text(system_prompt_soap), Part.from_text(user_prompt), Part.from_text(notes)],
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        soap_note = response.candidates[0].content.text
        return soap_note
    except Exception as e:
        logger.error(f"SOAP note creation error: {e}")
        raise Exception("Failed to create SOAP note")
