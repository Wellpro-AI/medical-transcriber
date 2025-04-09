# app/endpoints/medical_endpoints.py
from fastapi import APIRouter, HTTPException
from app.medical import extract_detailed_medical_data, create_soap_note
from pydantic import BaseModel
from app.utils import validate_medical_input
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class TranscriptionInput(BaseModel):
    transcription: str

class SoapNoteInput(BaseModel):
    transcription: str
    handwritten_notes:str 

@router.post("/extract-medical-data", tags=["Medical Data"])
async def extract_medical_data(input_data: TranscriptionInput):
    if not validate_medical_input(input_data.transcription):
         raise HTTPException(400, "Invalid medical content")
    try:
        medical_data = await extract_detailed_medical_data(input_data.transcription)
        return {"status": "success", "data": medical_data}
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-soap-note", tags=["Medical Data"])
async def create_soap_note_endpoint(input_data: SoapNoteInput):
    if not input_data.transcription or not input_data.handwritten_notes:
        raise HTTPException(
            status_code=400, 
            detail="Both transcription and handwritten notes are required"
        )
    if not validate_medical_input(input_data.transcription):
        raise HTTPException(400, "Invalid medical content")
    try:
        soap_note = await create_soap_note(input_data.transcription,input_data.handwritten_notes)
        return {"status": "success", "soap_note": soap_note}
    except Exception as e:
        logger.error(f"SOAP note creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create SOAP note")
