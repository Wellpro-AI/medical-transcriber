# app/config.py
import os

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# DEEPGRAM_API_KEY ="289db43d1cfa00d512c2b47241dfaa370c4df8e1" cpmmented out for security reasons
POOL_SIZE = 15
IDLE_TIMEOUT = 300
KEEPALIVE_INTERVAL = 1.0
MEDICAL_KEYWORDS = [
    "patient", "symptoms", "diagnosis", "treatment",
    "prescription", "doctor", "assessment", "blood pressure"
]
