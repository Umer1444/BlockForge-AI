"""
BlockForge AI – WebSocket Progress Streaming
"""

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings

router = APIRouter()
logger = logging.getLogger("blockforge.ws")


@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    Stream real-time processing progress via WebSocket.
    
    The Celery worker publishes updates to a Redis Pub/Sub channel
    named 'blockforge:progress:{job_id}'.  This endpoint subscribes
    to that channel and forwards every message to the connected client.
    """
    await websocket.accept()
    logger.info(f"⛏  WebSocket connected: job {job_id}")

    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    channel = f"blockforge:progress:{job_id}"

    try:
        await pubsub.subscribe(channel)

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Close connection when processing is done
                if data.get("state") in ("completed", "failed"):
                    logger.info(f"⛏  Job {job_id} {data['state']}. Closing WS.")
                    break

            # Send heartbeat every second to keep connection alive
            try:
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info(f"⛏  WebSocket disconnected: job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await websocket.send_json({"state": "error", "message": str(e)})
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await r.close()
