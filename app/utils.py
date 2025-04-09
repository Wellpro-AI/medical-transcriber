from app.config import MEDICAL_KEYWORDS,KEEPALIVE_INTERVAL
import asyncio
import logging

logger = logging.getLogger(__name__)


def validate_medical_input(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in MEDICAL_KEYWORDS) and len(text) < 10000

async def keepalive_task(dg_conn):
    """Safe connection maintenance"""
    silent_chunk = b'\x00' * 2048
    try:
        while True:
            await asyncio.sleep(KEEPALIVE_INTERVAL)
            try:
                # Attempt send as connection test
                dg_conn.send(silent_chunk)
            except Exception as e:
                logger.debug(f"Keepalive failed: {e}")
                break
    except Exception as e:
        logger.error(f"Keepalive error: {e}")
    finally:
        logger.debug("Keepalive task exiting")