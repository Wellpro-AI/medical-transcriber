# app/config.py
import os

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

POOL_SIZE = 15
IDLE_TIMEOUT = 300
KEEPALIVE_INTERVAL = 1.0
MEDICAL_KEYWORDS = [
    "patient", "symptoms", "diagnosis", "treatment",
    "prescription", "doctor", "assessment", "blood pressure"
]
