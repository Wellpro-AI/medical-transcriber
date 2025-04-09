# app/connection_manager.py
import asyncio
import time
from collections import deque, defaultdict
import logging
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from app.config import DEEPGRAM_API_KEY, POOL_SIZE, IDLE_TIMEOUT

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.pool = deque(maxlen=POOL_SIZE)
        self.lock = asyncio.Lock()
        self.dg_client = DeepgramClient(DEEPGRAM_API_KEY)
        asyncio.create_task(self._pool_maintenance())

# In ConnectionManager._get_connection():
    async def _get_connection(self):
        async with self.lock:
            now = time.time()
            while self.pool:
                entry = self.pool.popleft()
                if now - entry["last_used"] < IDLE_TIMEOUT:
                    # Verify connection is still alive
                    try:
                        entry["connection"].send(b'\x00' * 2048)
                        return entry["connection"]
                    except:
                        entry["connection"].finish()
            return self.dg_client.listen.live.v("1")

    async def _pool_maintenance(self):
        while True:
            await asyncio.sleep(IDLE_TIMEOUT // 2)
            async with self.lock:
                now = time.time()
                self.pool = deque(
                    [entry for entry in self.pool 
                     if now - entry["last_used"] < IDLE_TIMEOUT],
                    maxlen=POOL_SIZE
                )

    async def connect_normal(self, websocket: WebSocket):
        """Optimized for standard transcription"""
        await websocket.accept()
        dg_conn = await self._get_connection()
        
        # Original configuration with optimizations
        options = LiveOptions(
            model="nova-3",
            language="en-US",
            smart_format=True,
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=False  # Crucial for original behavior
        )
        
        dg_conn.start(options)
        
        self.active_connections[websocket] = {
            "dg_connection": dg_conn,
            "buffer": deque(maxlen=5)
        }
        
        loop = asyncio.get_running_loop()
        dg_conn.on(LiveTranscriptionEvents.Transcript,
            lambda _, result: asyncio.run_coroutine_threadsafe(
                self._handle_normal_transcript(websocket, result), loop
            )
        )
        dg_conn.on(LiveTranscriptionEvents.Error,
            lambda _, error: asyncio.run_coroutine_threadsafe(
                self._handle_error(websocket, error), loop
            )
        )
        
        return dg_conn

    async def connect_diarize(self, websocket: WebSocket):
        """Optimized for diarized transcription"""
        await websocket.accept()
        dg_conn = await self._get_connection()
        
        options = LiveOptions(
            model="nova-3",
            diarize=True,
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            smart_format=True,
            interim_results=False,
            endpointing=True,
            punctuate=True,
            vad_events=True
        )
        
        dg_conn.start(options)
        
        self.active_connections[websocket] = {
            "dg_connection": dg_conn,
            "buffer": deque(maxlen=5),
            "diarize": True,
            "speaker_phrases": defaultdict(list)
        }
        
        loop = asyncio.get_running_loop()
        # Fixed handler with explicit arguments
        dg_conn.on(LiveTranscriptionEvents.Transcript,
            lambda _, result: asyncio.run_coroutine_threadsafe(  # Explicit args
                self._handle_diarized_transcript(websocket, result), loop
            )
        )
        dg_conn.on(LiveTranscriptionEvents.Error,
            lambda _, error, *args: asyncio.run_coroutine_threadsafe(
                self._handle_error(websocket, error, *args), loop
            )
        )
        
        return dg_conn

    async def _handle_normal_transcript(self, websocket: WebSocket, result: Any):
        conn = self.active_connections.get(websocket)
        if not conn:
            return
            
        try:
            transcript = result.channel.alternatives[0].transcript
            if transcript.strip():
                # Maintain original message structure
                payload = {
                    "type": "transcript",
                    "data": transcript,
                    "is_final": result.is_final
                }
                await self._send_payload(websocket, payload)
        except Exception as e:
            logger.error(f"Transcript handling error: {e}")
    async def _handle_diarized_transcript(self, websocket: WebSocket, result: Any):
        """Process diarized transcription without duplicates"""
        conn = self.active_connections[websocket]
        try:
            # Clear previous partial results
            if not result.is_final:
                conn["speaker_phrases"].clear()

            words = getattr(result.channel.alternatives[0], "words", [])
            
            # Process current words only
            current_speakers = defaultdict(list)
            for word in words:
                speaker = getattr(word, "speaker", 0)
                current_speakers[speaker].append({
                    "word": word.word,
                    "start": word.start,
                    "end": word.end
                })

            # Update phrases with current state
            for speaker, words in current_speakers.items():
                conn["speaker_phrases"][speaker] = words  # Replace not append

            # Send only current state
            for speaker, words in conn["speaker_phrases"].items():
                if words:
                    phrase = " ".join(w["word"] for w in words)
                    start = words[0]["start"]
                    mins, secs = divmod(int(start), 60)
                    
                    await self._send_payload(websocket, {
                        "speaker": f"speaker_{speaker}",
                        "text": f"[{mins:02d}:{secs:02d}] {phrase}",
                        "is_final": result.is_final,
                        "timestamp": time.time()
                    })

            if result.is_final:
                conn["speaker_phrases"].clear()

        except Exception as e:
            logger.error(f"Diarized transcript error: {e}")

    async def _send_payload(self, websocket: WebSocket, payload: dict):
        """Managed payload delivery with buffering"""
        conn = self.active_connections[websocket]
        try:
            # Flush buffer first
            while conn["buffer"]:
                await websocket.send_json(conn["buffer"].popleft())
            # Send current
            await websocket.send_json(payload)
        except Exception as e:
            logger.warning(f"Buffering payload: {e}")
            if len(conn["buffer"]) < conn["buffer"].maxlen:
                conn["buffer"].append(payload)

    async def _handle_error(self, websocket: WebSocket,error:Any,*args):
        error_msg = f"{error} {' '.join(map(str, args))}" if args else str(error)

        await self._send_payload(websocket, {
            "type": "error",
            "data":error_msg
        })

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            entry = self.active_connections.pop(websocket)
            async with self.lock:
                if len(self.pool) < self.pool.maxlen:
                    self.pool.append({
                        "connection": entry["dg_connection"],
                        "last_used": time.time()
                    })
                else:
                    entry["dg_connection"].finish()

manager = ConnectionManager()