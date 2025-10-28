# Hybrid AI Refactor Guide

Purpose
-------
This guide explains the refactor path we will follow to make AI generation modular, testable, and safe for production. It assumes you have a working Python/Django development environment and the repository checked out.

High-level goal
----------------
- Extract AI provider code into `helpers/ai_clients.py`.
- Dependency-inject AI clients into `LessonGenerationService` and `HybridRoadmapService`.
- Move prompt builders and JSON repair utilities into `helpers/ai_prompts.py` and `helpers/json_utils.py`.
- Provide local fakes for tests and a containerized adapter for heavy media work.

Step-by-step (for a junior dev)
-------------------------------
1. Backup & branch
   - Create a backup branch before you start:
     ```powershell
     git checkout -b feature/refactor-ai-clients
     ```

2. Create `helpers/ai_clients.py` (skeleton)
   - Create a new file `skillsync-be/helpers/ai_clients.py` and implement a simple async interface:
     - Class: `AIClientManager`
     - Methods: `async generate(provider_name, prompt, json_mode=False, max_tokens=4096)`
     - Helpers: `async cleanup()` to close provider clients

   Example minimal class (conceptual):
   ```python
   # helpers/ai_clients.py
   class AIClientManager:
       def __init__(self, config):
           self.config = config
           self._clients = {}

       async def generate(self, provider, prompt, json_mode=False, max_tokens=4096):
           # lazily create provider client and call
           if provider == 'deepseek':
               # initialize and call
               pass
           elif provider == 'groq':
               pass
           elif provider == 'gemini':
               pass

       async def cleanup(self):
           # close all clients
           for c in self._clients.values():
               try:
                   await c.close()
               except Exception:
                   try:
                       c.close()
                   except Exception:
                       pass
   ```

3. Update `LessonGenerationService.__init__` to accept an `ai_clients` argument
   - Default behavior: if `ai_clients` is None, instantiate the current in-file clients as a compatibility fallback.
   - New signature:
     ```python
     def __init__(self, ai_clients: Optional[AIClientManager] = None, research_engine=None, media_processor=None):
         self.ai_clients = ai_clients or AIClientManager(config)
         self.research_engine = research_engine or multi_source_research_engine
         self.media_processor = media_processor or LocalMediaProcessor()
     ```

4. Replace direct provider calls with calls to `self.ai_clients.generate(...)`
   - For example, instead of `await self._generate_with_groq(...)` call `await self.ai_clients.generate('groq', prompt, json_mode, max_tokens)`.

5. Add unit tests
   - Create a fake `AIClientManager` that returns deterministic content for tests.
   - Update tests to inject the fake manager into `LessonGenerationService`.

6. Run tests and iterate
   - Run: `python -m pytest tests` or the repository's test commands.

Notes & gotchas
----------------
- Keep the public method signatures of `LessonGenerationService` unchanged to avoid touching call sites.
- Make cleanup idempotent. Tests will call `cleanup()` in teardown and it must not error if called multiple times.

Next steps after this refactor
-----------------------------
- Implement `MediaProcessor` interface and container adapter (see `Media_Worker_Guide.md`).
- Refactor `ai_roadmap_service.save_roadmap_to_db` to enqueue instead of generating eagerly.
