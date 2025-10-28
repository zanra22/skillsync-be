# Media Worker Guide

Purpose
-------
This guide explains how to build and operate the media worker that handles heavy native binaries (ffmpeg/yt-dlp) and long-running transcription tasks. The worker is intended to run in a container (ACI/AKS) and be invoked by a message queue (Azure Service Bus / Redis queue / Celery).

High level responsibilities
---------------------------
- Download media assets (YouTube, direct URLs)
- Extract audio and transform media using ffmpeg
- Run transcription (Groq Whisper or fallback)
- Upload artifacts to Blob Storage and return metadata

Design principles
------------------
- Single-purpose: the media worker should do one job and return a deterministic result.
- Idempotent: repeated work must be safe (create unique temp dirs and use atomic renames).
- Resource-limited: use process limits and timeouts to avoid runaway jobs.

Message schema (Service Bus / Redis)
------------------------------------
{
  "job_id": "uuid",
  "source": {
    "type": "youtube|http|upload",
    "url": "https://...",
    "metadata": {}
  },
  "actions": ["download","transcode","transcribe"],
  "callback_url": "https://backend/api/media/callback",
  "storage_path": "lessons/media/job_id/"
}

Worker skeleton (python)
-------------------------
1. Create a container image with these dependencies:
   - Python 3.11
   - ffmpeg static build (bundled in image)
   - yt-dlp
   - requests / aiohttp
   - Groq Whisper client or fallback scripts

2. Job loop (conceptual):
   - Receive message
   - Create temp dir
   - Download using `yt-dlp --no-playlist --no-warnings` or `requests` for direct URLs
   - Transcode audio with ffmpeg (stereo -> mono, 16k sample rate for Whisper)
   - Call transcription client
   - Upload artifacts (audio, transcript, thumbnails) to blob storage
   - POST a callback to `callback_url` with job_id and artifact locations

Timeouts & resource control
---------------------------
- Per-job timeout (configurable, e.g., 30 minutes).
- Limit memory/cpu via container orchestrator (AKS: resource limits; ACI: cpu/memory fields).
- Kill subprocess trees if timeout reached.

Error handling & retries
------------------------
- Use poison-queue pattern: after N failures, write to failed-jobs queue and notify via webhook.
- Capture stderr from ffmpeg/yt-dlp into logs and attach last 10 lines in the callback payload.

Security
--------
- Validate `callback_url` domain is in allowed list to prevent SSRF.
- Use managed identity or SAS tokens for blob storage uploads. Do not embed storage keys in messages.

Observability
-------------
- Emit job lifecycle events to Application Insights or your telemetry.
- Include job duration, bytes transferred, transcript length, and error codes.

Local dev & testing
--------------------
- Build the image locally and run a single-job consumer.
- Use a small YouTube sample to test flows; prefer `--max-downloads 1`.

Example dockerfile snippet
--------------------------
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg git build-essential
RUN pip install yt-dlp aiohttp requests
COPY worker.py /app/worker.py
CMD ["python","/app/worker.py"]
