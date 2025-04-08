# app/endpoints/websocket_endpoints.py
import asyncio
import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.connection_manager import ConnectionManager
from app.utils import keepalive_task

router = APIRouter()
manager = ConnectionManager()
logger = logging.getLogger(__name__)

# async def keepalive_task(dg_conn):
#     """Safe connection maintenance"""
#     silent_chunk = b'\x00' * 2048
#     try:
#         while True:
#             await asyncio.sleep(KEEPALIVE_INTERVAL)
#             try:
#                 # Attempt send as connection test
#                 dg_conn.send(silent_chunk)
#             except Exception as e:
#                 logger.debug(f"Keepalive failed: {e}")
#                 break
#     except Exception as e:
#         logger.error(f"Keepalive error: {e}")
#     finally:
#         logger.debug("Keepalive task exiting")

@router.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    """Original WebSocket endpoint with optimized internals"""
    keepalive = None
    try:
        dg_conn = await manager.connect_normal(websocket)
        keepalive = asyncio.create_task(keepalive_task(dg_conn))
        
        while True:
            data = await websocket.receive_bytes()
            try:
                # Original chunk handling with validation
                if len(data) in (2048, 4096):  # Common chunk sizes
                    dg_conn.send(data)
                else:
                    logger.warning(f"Unexpected chunk size: {len(data)}")
            except Exception as e:
                logger.error(f"Transmission error: {e}")
                await websocket.close(code=1011)
                break
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        if keepalive:
            keepalive.cancel()
        await manager.disconnect(websocket)

@router.websocket("/transcribe-diarize")
async def diarized_transcription(websocket: WebSocket):
    keepalive = None  # Initialize first
    try:
        # Let ConnectionManager handle the accept()
        dg_conn = await manager.connect_diarize(websocket)
        keepalive = asyncio.create_task(keepalive_task(dg_conn))
        
        while True:
            data = await websocket.receive_bytes()
            try:
                dg_conn.send(data)
            except Exception as e:
                logger.error(f"Audio send error: {e}")
                await websocket.close(code=1011)
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if keepalive:
            keepalive.cancel()
        await manager.disconnect(websocket)