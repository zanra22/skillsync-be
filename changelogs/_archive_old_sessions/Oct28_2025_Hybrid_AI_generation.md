# Changelog - Oct 28, 2025

Summary
-------
- Purpose: Record, explain, and provide runbook for the backend changes made to harden hybrid AI roadmap & lesson generation, add resource cleanup, normalize total_duration for DB safety, and prepare for lazy-loading background generation.
- Scope: changes touch AI services, lesson/roadmap persistence, DB models/migrations, onboarding/tests, and CI/dev tooling references.

Files changed (high level)
--------------------------
- `helpers/ai_lesson_service.py` — major: hybrid AI generation, multi-source research integration, transcription fallbacks, JSON repair, and explicit async cleanup().
- `helpers/ai_roadmap_service.py` — major: total_duration normalization, guaranteed cleanup of lesson clients, and safer persistence logic that prepares for lazy enqueueing.
- `lessons/models.py` — schema additions (module/lesson fields) and migrations prepared (untracked migration files present).
- `lessons/mutation.py`, `lessons/query.py`, `lessons/types.py` — wiring changes to support new fields and generation flows.
- `onboarding/*`, `profiles/*`, `users/*` — small compatibility and types adjustments to supply user_profile data into generation flows.
- `helpers/email_service.py` & `tests/*` — test harness and email/resend tests updated to reflect new flows and cleanup.
- `core/settings/dev.py`, `config/security.py`, `config/constants.py` — dev and security adjustments for environment variables and local debug of AI clients.
- `Procfile`, `requirements.txt` — runtime changes: new dependencies and process hints for containerized workers.

Why these changes
-----------------
- Real-world AI runs were producing long/verbose `total_duration` strings that violated DB varchar(50) constraints. We added prompt enforcement + normalization to ensure DB-safe, short values (e.g., "8-10 weeks").
- Long-running AI calls and subprocesses (yt-dlp + ffmpeg) caused stale DB connections and Windows Proactor finalizer warnings. We added `close_old_connections()` around heavy I/O and async `cleanup()` methods to close HTTP clients.
- Tests were fragile due to event-loop closing and dangling async clients — cleanup and test-teardown adjustments were made.
- To reduce LLM cost and improve UX we designed a lazy-loading strategy (skeleton-first + background per-module generation). The code changes prepare persistence and cleanup for that future flow.

Important implementation notes (by file)
--------------------------------------

helpers/ai_lesson_service.py
- What changed:
  - Integrated multi-source research engine calls prior to generation to improve factual accuracy and provide source attribution to lessons.
  - Hybrid multi-provider generation with fallback order: DeepSeek (OpenRouter) → Groq → Gemini. Each provider is lazily initialized.
  - Robust YouTube transcript handling: prefer YouTube captions, fallback to Groq Whisper transcription (yt-dlp + ffmpeg). Added rate-limits and retries.
  - JSON extraction/repair for LLM outputs with defensive parsing. Each generator tries to extract JSON from ```json blocks, bare JSON, or repairs malformed outputs.
  - Added `async cleanup()` to close async client instances (_deepseek_client, _groq_client, _gemini_client) to avoid Proactor finalizer warnings on Windows.

- Why it matters:
  - Improves lesson accuracy and traceability (source attribution).
  - Prevents resource leakage and noisy event-loop finalizer errors during tests and long-running processes.

- Developer notes / example usage:
  - To generate a lesson manually in a Django shell (sync wrapper):
    1. Open Django shell: `python manage.py shell`
    2. Run:
       ```python
       from helpers.ai_lesson_service import LessonGenerationService, LessonRequest
       svc = LessonGenerationService()
       req = LessonRequest(step_title='Intro to SQL', lesson_number=1, learning_style='hands_on', user_profile={'time_commitment':'3-5','learning_style':'hands_on'})
       import asyncio
       lesson = asyncio.run(svc.generate_lesson(req))
       print(lesson.keys())
       asyncio.run(svc.cleanup())
       ```

helpers/ai_roadmap_service.py
- What changed:
  - Added `_normalize_total_duration()` and `_enforce_total_duration_prompt()` to enforce DB-safe `total_duration` values.
  - `save_roadmap_to_db()` now normalizes `total_duration` before persisting and wraps lesson generation in try/finally to guarantee `lesson_service.cleanup()` is awaited.
  - Prepared persistence code to create skeleton modules and lessons but left a path to switch to lazy enqueueing later.

- Why it matters:
  - Removes the Postgres error caused by strings longer than varchar(50).
  - Ensures AI clients are closed even on exceptions, reducing flaky event-loop finalizer warnings in tests.

- Developer notes / example commands:
  - Run the existing pipeline test to validate save behavior:
    ```powershell
    python .\test_complete_pipeline.py
    ```

lessons/models.py & migrations
- What changed:
  - Module/LessonContent models gained fields used by lazy-generation and status tracking (new migration files appear in untracked list).

- Why it matters:
  - These fields are required for the lazy-loading design (generation_status, generation_job_id, artifact_url, etc.).

- Developer notes / migrations:
  - Ensure migrations are applied in dev/staging before running new code:
    ```powershell
    python manage.py makemigrations lessons
    python manage.py migrate
    ```
  - If you see untracked migration files in `git status` and you didn't create them intentionally, inspect and commit them to keep schema in sync.

Tests
-----
- What changed:
  - Updated tests to avoid manually closing the event loop. Tests now cancel pending tasks and rely on the new `cleanup()` methods.
- Why it matters:
  - Prevents "Event loop is closed" finalizer warnings on Windows and makes test teardown more robust.

Dev & security tweaks
--------------------
- `core/settings/dev.py`, `config/security.py`, `config/constants.py` updated to include debug-friendly settings for AI clients and to make cookie/token policies explicit for local runs.
- `Procfile` adjusted to include notes for worker processes (media worker) and Function App hooks.

Runbook / How to test locally (step-by-step)
-------------------------------------------
1. Create a snapshot branch before making further refactors (recommended):
   ```powershell
   git checkout -b backup/before-ai-refactor
   git add -A
   git commit -m "chore: backup before AI refactor (2025-10-28)"
   git push -u origin backup/before-ai-refactor
   ```
2. Ensure migrations are applied:
   ```powershell
   python manage.py migrate
   ```
3. Run the pipeline test (smoke):
   ```powershell
   python .\test_full_user_journey_pipeline.py
   ```
4. Manual lesson generation run (see helper example in `helpers/ai_lesson_service.py` section above).

Rollback plan
-------------
- If the refactor introduces regressions, revert to the backup branch or reset to the commit created in step 1:
  ```powershell
  git checkout master
  git reset --hard origin/master
  git checkout backup/before-ai-refactor
  ```

Notes & next steps
------------------
- Immediate next work: implement `helpers/ai_clients.py` and refactor `LessonGenerationService` to accept injected clients (improves testability and modularity).
- Implement DB migration to add module generation status fields and change `save_roadmap_to_db` to enqueue per-module generation jobs instead of generating eagerly.
- Implement containerized media worker and Durable Functions orchestration per `Concrete Architecture Plan_Lazy_Loading_with_Azure_Functions.md`.

Prepared by the engineering team — 2025-10-28
