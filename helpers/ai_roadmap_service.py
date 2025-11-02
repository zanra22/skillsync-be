import logging
from lessons.models import Roadmap as RoadmapModel, Module as ModuleModel, LessonContent as LessonModel
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import os
import requests
import uuid
import hashlib
from datetime import datetime
from django.utils import timezone  # ✅ NEW: For timezone-aware datetimes
from dataclasses import dataclass

# Azure Service Bus integration
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity import DefaultAzureCredential

"""
🚀 MONGODB SCHEMA PREPARATION NOTES:

When implementing MongoDB integration, we'll need these collections:

1. learning_roadmaps:
   - user_id (string): Reference to Django User.id
   - goal_id (string): Reference to UserLearningGoal.id
   - skill_name (string): The skill being learned
   - description (string): Overview of the learning journey
   - total_duration (string): Estimated completion time
   - difficulty_level (string): beginner|intermediate|advanced
   - steps (array): Array of learning steps
     - title (string): Step name
     - description (string): Detailed step description
     - estimated_duration (string): Time for this step
     - difficulty (string): Step difficulty level
     - resources (array of strings): Learning resources
     - skills_covered (array of strings): Skills gained in this step
   - generated_at (datetime): When roadmap was created
   - user_profile_snapshot (object): User context when generated
     - role (string)
     - industry (string)
     - career_stage (string)
     - learning_style (string)
     - time_commitment (string)
   - ai_model_version (string): Track which AI model/prompt version
   - status (string): active|completed|archived
   - progress (object): User progress tracking
     - current_step (number): Which step user is on
     - completed_steps (array): Array of completed step indices
     - started_at (datetime)
     - last_updated (datetime)

2. roadmap_feedback:
   - roadmap_id (ObjectId): Reference to learning_roadmaps
   - user_id (string): Reference to Django User.id
   - rating (number): 1-5 stars
   - feedback_text (string): User comments
   - created_at (datetime)

The logging below will help us validate this structure matches Gemini's output.
"""

logger = logging.getLogger(__name__)
@dataclass
class LearningGoal:
    skill_name: str
    description: str
    target_skill_level: str
    priority: int

@dataclass
class UserProfile:
    user_id: str  # ✅ NEW: Track which user generated this roadmap
    email: str  # ✅ NEW: Alternative identifier for user
    role: str
    industry: str
    career_stage: str
    learning_style: str
    time_commitment: str
    goals: List['LearningGoal']

@dataclass
class RoadmapStep:
    title: str
    description: str
    estimated_duration: str
    difficulty: str
    resources: List[str] = field(default_factory=lambda: ["No resources specified yet. Waiting for the lessons to be generated first."])
    skills_covered: List[str] = field(default_factory=list)

@dataclass
class LearningRoadmap:
    skill_name: str
    description: str
    total_duration: str
    difficulty_level: str
    steps: List['RoadmapStep']

# =============================
# HYBRID AI ROADMAP SERVICE
# =============================

class HybridRoadmapService:
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self._deepseek_client = None
        self._groq_client = None
        self._last_deepseek_call = None
        self._last_gemini_call = None
        self._model_usage = {'deepseek_v31': 0, 'groq': 0, 'gemini': 0}
        if not self.gemini_api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found - Gemini fallback unavailable")
        if not self.groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY not found - Groq fallback unavailable")
        if not self.openrouter_api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY not found - DeepSeek unavailable")

    async def cleanup(self):
        """
        Best-effort cleanup for any async clients created by the HybridRoadmapService.
        Call this before shutting down the event loop to avoid Windows Proactor finalizer warnings.
        """
        # Close DeepSeek/OpenRouter client
        if getattr(self, '_deepseek_client', None):
            try:
                await self._deepseek_client.close()
                logger.debug("🧹 Closed DeepSeek/OpenRouter client")
            except Exception:
                try:
                    self._deepseek_client.close()
                except Exception:
                    pass
            finally:
                self._deepseek_client = None

        # Close Groq client
        if getattr(self, '_groq_client', None):
            try:
                await self._groq_client.close()
                logger.debug("🧹 Closed Groq client")
            except Exception:
                try:
                    self._groq_client.close()
                except Exception:
                    pass
            finally:
                self._groq_client = None

    async def generate_full_roadmap_modules_lessons(self, user_profile):
        """
        Generate a full roadmap, modules, and lessons for the given user profile.
        Returns: (roadmap_obj, modules, lessons_by_module)
        """
        # Generate roadmap (use first goal if multiple)
        if hasattr(user_profile, 'goals') and user_profile.goals:
            goal = user_profile.goals[0]
        else:
            raise ValueError("UserProfile must have at least one LearningGoal in 'goals'.")
        # Use existing roadmap generation logic (sync or async)
        roadmap = None
        if hasattr(self, 'generate_roadmap'):
            roadmap = self.generate_roadmap(user_profile)
        elif hasattr(self, 'generate_roadmaps'):
            roadmaps = await self.generate_roadmaps(user_profile)
            roadmap = roadmaps[0] if roadmaps else None
        if not roadmap:
            raise ValueError("Failed to generate roadmap for user profile.")
        # Persist roadmap, modules, and lessons
        return await self.save_roadmap_to_db(user_profile, roadmap)

    async def save_roadmap_to_db(self, user_profile, roadmap):
        """
        Save a single roadmap, its modules, and lessons to the database.
        Returns: (roadmap_obj, modules, lessons_by_module)
        """
        from lessons.models import Roadmap as RoadmapModel, Module as ModuleModel, LessonContent as LessonModel
        import re

        # --- Ensure total_duration is normalized to a short machine-friendly format ---
        try:
            raw_total = getattr(roadmap, 'total_duration', '') or ''
            normalized_total = self._normalize_total_duration(raw_total)
            if normalized_total != raw_total:
                logger.debug(f"[RoadmapSave] Normalized total_duration: '{raw_total}' -> '{normalized_total}'")
            # write-back to the roadmap object if possible
            try:
                setattr(roadmap, 'total_duration', normalized_total)
            except Exception:
                # not critical if roadmap is a dict or immutable; we'll use normalized_total when persisting
                pass
        except Exception as e:
            logger.debug(f"Error normalizing total_duration: {e}")
            normalized_total = ''

        # 1. Create or get roadmap
        goal_input = getattr(roadmap, 'skill_name', '')
        ai_title = await self.generate_title_from_goal(goal_input)
        cache_key = RoadmapModel.generate_cache_key(
            title=goal_input,
            user_id=str(getattr(user_profile, 'user_id', '')),
            goal_id=str(getattr(getattr(roadmap, 'goal', None), 'goal_id', '')),
            difficulty_level=str(getattr(roadmap, 'difficulty_level', None))
        )
        roadmap_obj = await RoadmapModel.objects.filter(cache_key=cache_key).afirst()
        if not roadmap_obj:
            logger.info(f"[Roadmap] total_duration: {getattr(roadmap, 'total_duration', '')}")
            logger.info(f"[Roadmap] ai_model_version: {'gemini-2.0-flash-exp'}")
            roadmap_obj = await RoadmapModel.objects.acreate(
                title=ai_title,
                goal_input=goal_input,
                description=roadmap.description,
                user_id=getattr(user_profile, 'user_id', ''),
                goal_id=getattr(getattr(roadmap, 'goal', None), 'goal_id', ''),
                difficulty_level=getattr(roadmap, 'difficulty_level', None),
                total_duration=getattr(roadmap, 'total_duration', ''),
                cache_key=cache_key
            )

        modules = []
        lessons_by_module = {}
        
        def parse_duration(duration_str):
            week_match = re.search(r"(\d+)(?:-(\d+))?\s*weeks?", duration_str)
            hour_match = re.search(r"(\d+)(?:-(\d+))?\s*hours?/week", duration_str)
            weeks = 2
            hours_per_week = 5
            if week_match:
                if week_match.group(2):
                    weeks = (int(week_match.group(1)) + int(week_match.group(2))) // 2
                else:
                    weeks = int(week_match.group(1))
            if hour_match:
                if hour_match.group(2):
                    hours_per_week = (int(hour_match.group(1)) + int(hour_match.group(2))) // 2
                else:
                    hours_per_week = int(hour_match.group(1))
            return weeks * hours_per_week

        for idx, step in enumerate(getattr(roadmap, 'steps', [])):
            module_cache_key = ModuleModel.generate_cache_key(
                roadmap_id=str(roadmap_obj.id),
                title=step.title,
                order=idx+1,
                difficulty=step.difficulty
            )
            module_obj = await ModuleModel.objects.filter(cache_key=module_cache_key).afirst()
            if not module_obj:
                # Create module with generation_status set to 'not_started'
                module_obj = await ModuleModel.objects.acreate(
                    roadmap=roadmap_obj,
                    title=step.title,
                    order=idx+1,
                    difficulty=step.difficulty,
                    description=getattr(step, 'description', ''),
                    cache_key=module_cache_key,
                    generation_status='not_started'
                )
            modules.append(module_obj)

            # ON-DEMAND GENERATION STRATEGY:
            # Don't enqueue modules immediately - lessons will be generated
            # when user clicks on module (via separate GraphQL mutation)
            # This saves 60-80% on AI costs by only generating what users view

            # Return empty lessons for now - they'll be generated on-demand
            lessons_by_module[module_obj.title] = []

        logger.info(f"[RoadmapSave] Modules created: {len(modules)}. Lessons will be generated on-demand when user views modules.")
        return roadmap_obj, modules, lessons_by_module
    
    async def enqueue_module_for_generation(self, module_obj, user_profile):
        """
        Enqueue lessons for a module via Azure Service Bus.
        Called when user clicks "Generate" button to generate lessons for a specific module.
        """
        # Generate idempotency key to prevent duplicate processing
        idempotency_key = self._generate_idempotency_key(module_obj)

        # Update module with queued status and idempotency key
        module_obj.generation_status = 'queued'
        module_obj.idempotency_key = idempotency_key
        module_obj.generation_started_at = timezone.now()  # ✅ FIXED: Use timezone-aware datetime
        await module_obj.asave()

        # Prepare message for Azure Service Bus (lesson-generation queue)
        message_data = {
            'module_id': module_obj.id,
            'roadmap_id': module_obj.roadmap.id,
            'title': module_obj.title,
            'description': module_obj.description,
            'difficulty': module_obj.difficulty,
            'order': module_obj.order,
            'user_id': module_obj.roadmap.user_id,
            'user_profile': self._serialize_user_profile(user_profile),
            'idempotency_key': idempotency_key,
            'timestamp': timezone.now().isoformat()  # ✅ FIXED: Use timezone-aware datetime
        }

        # Send message to Azure Service Bus (lesson-generation queue)
        await self._send_to_service_bus(message_data, 'lesson-generation')

        logger.info(f"[ServiceBus] Lessons queued for module '{module_obj.title}' with idempotency key: {idempotency_key}")
    
    def _generate_idempotency_key(self, module_obj):
        """Generate a unique idempotency key for the module."""
        key_components = [
            str(module_obj.id),
            str(module_obj.roadmap.id),
            module_obj.title,
            str(module_obj.order),
            str(datetime.now().timestamp())
        ]
        key_string = ":".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _serialize_user_profile(self, user_profile):
        """Convert user profile to serializable dictionary."""
        if hasattr(user_profile, '__dict__'):
            # Convert dataclass or object to dict
            profile_dict = {}
            for key in ['role', 'industry', 'career_stage', 'learning_style', 'time_commitment']:
                if hasattr(user_profile, key):
                    profile_dict[key] = getattr(user_profile, key)
            
            # Handle goals separately as they might be objects
            if hasattr(user_profile, 'goals') and user_profile.goals:
                goals = []
                for goal in user_profile.goals:
                    if hasattr(goal, '__dict__'):
                        goals.append({
                            'skill_name': getattr(goal, 'skill_name', ''),
                            'description': getattr(goal, 'description', ''),
                            'target_skill_level': getattr(goal, 'target_skill_level', ''),
                            'priority': getattr(goal, 'priority', 0)
                        })
                    else:
                        goals.append(goal)
                profile_dict['goals'] = goals
            
            return profile_dict
        return user_profile  # Already a dict or JSON-serializable
    
    async def _send_to_service_bus(self, message_data, queue_name):
        """
        Send a message to Azure Service Bus.
        Falls back to direct processing if Service Bus is not configured.
        """
        service_bus_conn_str = os.getenv('AZURE_SERVICE_BUS_CONNECTION_STRING')

        if not service_bus_conn_str:
            logger.warning("⚠️ AZURE_SERVICE_BUS_CONNECTION_STRING not found - falling back to direct processing")
            # TODO: Implement direct processing fallback
            return

        # Debug: Log that we have the connection string (without exposing the full key)
        logger.debug(f"[ServiceBus] Using connection string from env (starts with: {service_bus_conn_str[:50]}...)")
        
        try:
            # Create a Service Bus client
            service_bus_client = ServiceBusClient.from_connection_string(service_bus_conn_str)

            # ✅ FIXED: Use async context manager for async code
            async with service_bus_client:
                sender = service_bus_client.get_queue_sender(queue_name=queue_name)

                # Create a message with the serialized data
                message = ServiceBusMessage(json.dumps(message_data))

                # Send the message using async context
                async with sender:
                    await sender.send_messages(message)

            logger.info(f"[ServiceBus] Message sent to queue '{queue_name}' successfully")
        except Exception as e:
            logger.error(f"❌ Error sending message to Azure Service Bus: {e}")
            # Update module status to reflect the error
            try:
                module_id = message_data.get('module_id')
                if module_id:
                    module = await ModuleModel.objects.filter(id=module_id).afirst()
                    if module:
                        module.generation_status = 'failed'
                        module.generation_error = f"Failed to enqueue: {str(e)}"
                        await module.asave()
            except Exception as inner_e:
                logger.error(f"❌ Error updating module status: {inner_e}")

    async def generate_title_from_goal(self, goal_input: str) -> str:
        """
        Use Hybrid AI to generate a meaningful roadmap title from the raw goal input.
        """
        import re
        keywords = re.findall(r'Python|JavaScript|Data Science|Career|Development|Beginner|Advanced', goal_input, re.IGNORECASE)
        if keywords:
            base = ' '.join(keywords)
            return f"{base.title()} Roadmap"
        return f"{goal_input.strip().title()} Roadmap"

    async def generate_title_from_goal(self, goal_input: str) -> str:
        """
        Use Hybrid AI to generate a meaningful roadmap title from the raw goal input.
        """
        import re
        keywords = re.findall(r'Python|JavaScript|Data Science|Career|Development|Beginner|Advanced', goal_input, re.IGNORECASE)
        if keywords:
            base = ' '.join(keywords)
            return f"{base.title()} Roadmap"
        return f"{goal_input.strip().title()} Roadmap"

    def _clean_json_string(self, json_str: str) -> str:
        """
        Clean malformed JSON strings from AI output.
        Fixes common issues like:
        - Extra spaces in key names: " "description" → "description"
        - Trailing commas: [1,2,] → [1,2]
        """
        # Fix malformed keys with extra spaces/quotes
        # Pattern: " "key": → "key":
        json_str = re.sub(r'"\s+"([^"]+)":', r'"\1":', json_str)

        # Remove any trailing commas before closing brackets/braces
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Fix escaped quotes in values that shouldn't be escaped
        json_str = re.sub(r'\\"([^"]+)\\"', r'"\1"', json_str)

        return json_str

    def _parse_ai_response(self, ai_text: str, goal: LearningGoal) -> Optional[LearningRoadmap]:
        """
        Parse AI-generated text into structured roadmap data with enhanced error handling.
        """
        try:
            logger.info(f"🔍 Parsing AI response for {goal.skill_name}")
            # Try multiple extraction methods for JSON
            json_data = None
            # Method 1: Look for JSON code block
            code_block_pattern = r'```json\s*(\{.*?\})\s*```'
            import re
            matches = re.findall(code_block_pattern, ai_text, re.DOTALL | re.IGNORECASE)
            if matches:
                json_data = matches[0]
                logger.info("✅ Found JSON in code block")
            else:
                # Method 2: Look for raw JSON
                start_idx = ai_text.find('{')
                end_idx = ai_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_data = ai_text[start_idx:end_idx]
                    logger.info("✅ Found raw JSON")
                else:
                    logger.error("❌ No JSON structure found in AI response")
                    logger.debug(f"AI Response preview: {ai_text[:200]}...")
                    return None
            # Clean up the JSON string
            if json_data:
                # Use the JSON cleaning function
                json_data = self._clean_json_string(json_data)
                # 🚀 LOG THE EXTRACTED JSON FOR DEBUGGING
                logger.info(f"🔍 EXTRACTED JSON for {goal.skill_name}:")
                logger.info("-" * 50)
                logger.info(json_data)
                logger.info("-" * 50)
                # Parse the JSON
                roadmap_data = json.loads(json_data)
                # Validate required fields
                required_fields = ['skill_name', 'description', 'total_duration', 'difficulty_level', 'steps']
                missing_fields = [field for field in required_fields if field not in roadmap_data]
                if missing_fields:
                    logger.warning(f"⚠️ Missing fields in AI response: {missing_fields}")
                    # Fill in missing fields with defaults
                    if 'skill_name' not in roadmap_data:
                        roadmap_data['skill_name'] = goal.skill_name
                    if 'description' not in roadmap_data:
                        roadmap_data['description'] = f"Learning path for {goal.skill_name}"
                    if 'total_duration' not in roadmap_data:
                        roadmap_data['total_duration'] = "8-12 weeks"
                    if 'difficulty_level' not in roadmap_data:
                        roadmap_data['difficulty_level'] = goal.target_skill_level
                    if 'steps' not in roadmap_data:
                        roadmap_data['steps'] = []
                # Create structured roadmap steps
                steps = []
                import re
                for i, step_data in enumerate(roadmap_data.get('steps', [])):
                    # Validate step data
                    raw_title = step_data.get('title', f'Step {i+1}')
                    # Extract descriptive title after 'Step N:' if present
                    match = re.match(r"Step\s*\d+\s*:\s*(.+)", raw_title)
                    step_title = match.group(1).strip() if match else raw_title.strip()
                    step_description = step_data.get('description', 'Learning step description')
                    step_duration = step_data.get('estimated_duration', '1-2 weeks')
                    step_difficulty = step_data.get('difficulty', 'intermediate')
                    step_skills = step_data.get('skills_covered', [])
                    if not isinstance(step_skills, list):
                        step_skills = [str(step_skills)] if step_skills else []
                    step = RoadmapStep(
                        title=step_title,
                        description=step_description,
                        estimated_duration=step_duration,
                        difficulty=step_difficulty,
                        skills_covered=step_skills
                    )
                    steps.append(step)
                roadmap = LearningRoadmap(
                    skill_name=goal.skill_name,
                    description=roadmap_data.get('description', ''),
                    total_duration=roadmap_data.get('total_duration', ''),
                    difficulty_level=roadmap_data.get('difficulty_level', goal.target_skill_level),
                    steps=steps
                )
                logger.info(f"✅ Successfully parsed roadmap with {len(steps)} steps")
                return roadmap
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.debug(f"Attempted to parse: {json_data[:500] if 'json_data' in locals() and json_data else 'No JSON data'}...")
            return None
        except Exception as e:
                            # Always return a non-empty list for resources (never None or empty)
                            step_resources = step_data.get('resources')
                            if not isinstance(step_resources, list) or not step_resources:
                                step_resources = ["No resources specified yet. Waiting for the lessons to be generated first."]
                            step = RoadmapStep(
                                title=step_title,
                                description=step_description,
                                estimated_duration=step_duration,
                                difficulty=step_difficulty,
                                resources=step_resources,
                                skills_covered=step_skills
                            )

    def _get_fallback_roadmaps(self, user_profile: UserProfile) -> List[LearningRoadmap]:
        logger.info("🔄 Using fallback roadmaps")
        roadmaps = []
        for goal in user_profile.goals:
            fallback = self._get_fallback_roadmap(goal)
            if fallback:
                roadmaps.append(fallback)
        return roadmaps

    def _get_fallback_roadmap(self, goal: LearningGoal) -> LearningRoadmap:
        # Create a generic roadmap structure
        steps = [
            RoadmapStep(
                title="Foundation & Basics",
                description=f"Learn the fundamental concepts of {goal.skill_name}",
                estimated_duration="2-3 weeks",
                difficulty="beginner",
                resources=[
                    "Official documentation",
                    "Beginner tutorials",
                    "Practice exercises"
                ],
                skills_covered=[f"Basic {goal.skill_name}", "Core concepts"]
            ),
            RoadmapStep(
                title="Hands-on Practice",
                description=f"Apply {goal.skill_name} through practical projects",
                estimated_duration="3-4 weeks",
                difficulty="intermediate",
                resources=[
                    "Project tutorials",
                    "Online courses",
                    "Practice platforms"
                ],
                skills_covered=[f"Practical {goal.skill_name}", "Problem solving"]
            ),
            RoadmapStep(
                title="Advanced Concepts",
                description=f"Master advanced {goal.skill_name} techniques",
                estimated_duration="2-3 weeks",
                difficulty="advanced",
                resources=[
                    "Advanced tutorials",
                    "Best practices guides",
                    "Community resources"
                ],
                skills_covered=[f"Advanced {goal.skill_name}", "Optimization"]
            )
        ]
        return LearningRoadmap(
            skill_name=goal.skill_name,
            description=f"A structured path to master {goal.skill_name} from {goal.target_skill_level} level",
            total_duration="7-10 weeks",
            difficulty_level=goal.target_skill_level,
            steps=steps
        )
    def generate_roadmap(self, user_profile: 'UserProfile'):
        """
        Synchronous wrapper for async generate_roadmaps for legacy/test compatibility.
        Returns the first roadmap (single-goal use case).
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            roadmaps = loop.run_until_complete(self.generate_roadmaps(user_profile))
        else:
            roadmaps = asyncio.run(self.generate_roadmaps(user_profile))
        return roadmaps[0] if roadmaps else None

    """
    Async hybrid AI fallback for roadmap generation (DeepSeek > Groq > Gemini)
    """
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self._deepseek_client = None
        self._groq_client = None
        self._last_deepseek_call = None
        self._last_gemini_call = None
        self._model_usage = {'deepseek_v31': 0, 'groq': 0, 'gemini': 0}
        if not self.gemini_api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found - Gemini fallback unavailable")
        if not self.groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY not found - Groq fallback unavailable")
        if not self.openrouter_api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY not found - DeepSeek unavailable")

    async def generate_roadmaps(self, user_profile: UserProfile) -> List[LearningRoadmap]:
        """
        Generate personalized learning roadmaps for all user goals using hybrid AI fallback.
        Adds robust error logging and resource usage checks.
        """
        import traceback
        import psutil
        roadmaps = []
        process = psutil.Process()
        logger.info(f"[Resource] Memory usage before roadmap generation: {process.memory_info().rss / 1024 ** 2:.2f} MB")
        for goal in user_profile.goals:
            try:
                roadmap = await self._generate_single_roadmap(user_profile, goal)
                if roadmap:
                    roadmaps.append(roadmap)
            except Exception as e:
                logger.error(f"❌ Failed to generate roadmap for {goal.skill_name}: {e}")
                logger.error(traceback.format_exc())
                # Log resource usage at failure
                logger.error(f"[Resource] Memory usage at failure: {process.memory_info().rss / 1024 ** 2:.2f} MB")
                # Optionally log DB connection status if using Django ORM
                try:
                    from django.db import connection
                    if not connection.is_usable():
                        logger.error("❌ Database connection is not usable!")
                except Exception as db_exc:
                    logger.error(f"[DB] Error checking DB connection: {db_exc}")
                fallback = self._get_fallback_roadmap(goal)
                if fallback:
                    roadmaps.append(fallback)
        logger.info(f"[Resource] Memory usage after roadmap generation: {process.memory_info().rss / 1024 ** 2:.2f} MB")
        return roadmaps

    async def _generate_single_roadmap(self, user_profile: UserProfile, goal: LearningGoal) -> Optional[LearningRoadmap]:
        logger.info(f"🤖 Generating roadmap for: {goal.skill_name}")
        prompt = self._create_roadmap_prompt(user_profile, goal)
        # Enforce stricter output for total_duration at the prompt level to avoid long sentences
        try:
            prompt = self._enforce_total_duration_prompt(prompt)
        except Exception:
            pass
        try:
            # Try DeepSeek V3.1 (OpenRouter)
            if self.openrouter_api_key:
                try:
                    content = await self._generate_with_deepseek_v31(prompt)
                    self._model_usage['deepseek_v31'] += 1
                    logger.info("✅ DeepSeek V3.1 roadmap success")
                    return self._parse_ai_response(content, goal)
                except Exception as e:
                    logger.warning(f"⚠️ DeepSeek V3.1 error: {e}, falling back to Groq")
            # Fallback to Groq
            if self.groq_api_key:
                try:
                    content = await self._generate_with_groq(prompt)
                    self._model_usage['groq'] += 1
                    logger.info("✅ Groq roadmap success")
                    return self._parse_ai_response(content, goal)
                except Exception as e:
                    logger.warning(f"⚠️ Groq error: {e}, falling back to Gemini")
            # Final fallback to Gemini
            if self.gemini_api_key:
                content = await self._generate_with_gemini(prompt)
                self._model_usage['gemini'] += 1
                logger.info("✅ Gemini roadmap success")
                return self._parse_ai_response(content, goal)
            logger.error("❌ No AI provider available for roadmap generation")
            return None
        except Exception as e:
            logger.error(f"❌ Error in hybrid roadmap generation: {e}")
            return None

    async def _generate_with_deepseek_v31(self, prompt: str, max_tokens: int = 4096) -> str:

        def _normalize_total_duration(self, raw_total: str) -> str:
            """
            Normalize an AI-provided total_duration into a concise, DB-safe format.

            Expected outputs:
            - "8-10 weeks"
            - "5 weeks"

            If the AI returned a sentence like "Approximately 8-10 weeks at your pace, ...",
            this function will extract the numeric range or single number and format it.
            Falls back to truncating the raw string to 50 chars if no numeric info is found.
            """
            if not raw_total or not isinstance(raw_total, str):
                return ""

            raw = raw_total.strip()
            # 1) Range with hyphen: 8-10 weeks, 8 - 10 weeks, approximately 8-10 weeks
            m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*weeks?", raw, re.IGNORECASE)
            if m:
                a, b = m.group(1), m.group(2)
                return f"{int(a)}-{int(b)} weeks"

            # 2) Single number: '5 weeks' or '5 week'
            m2 = re.search(r"(\d{1,2})\s*weeks?", raw, re.IGNORECASE)
            if m2:
                return f"{int(m2.group(1))} weeks"

            # 3) If contains two numbers separated by space or words, use first two as range
            nums = re.findall(r"\d{1,2}", raw)
            if len(nums) >= 2:
                return f"{int(nums[0])}-{int(nums[1])} weeks"
            if len(nums) == 1:
                return f"{int(nums[0])} weeks"

            # 4) As a last resort, truncate to 50 chars to fit DB
            return raw[:50]

        def _enforce_total_duration_prompt(self, prompt: str) -> str:
            """
            Append a short instruction to the roadmap prompt to force the model to return
            a concise machine-friendly `total_duration` value (e.g. "8-10 weeks" or "5 weeks").
            """
            if not prompt:
                return prompt
            instruction = (
                "\n\nSTRICT OUTPUT INSTRUCTION: When you include the field `total_duration`,"
                " output ONLY a short value in one of these formats: '8-10 weeks' or '5 weeks'."
                " Do NOT output a sentence or extra commentary. Use digits and the word 'weeks'."
            )
            return prompt + instruction
        try:
            from openai import AsyncOpenAI
        except Exception as ie:
            logger.warning("⚠️ openai/OpenRouter client not available: %s", ie)
            raise RuntimeError("DeepSeek/OpenRouter client not available") from ie
        from datetime import datetime
        import asyncio
        if self._last_deepseek_call:
            elapsed = (datetime.now() - self._last_deepseek_call).total_seconds()
            if elapsed < 3:
                await asyncio.sleep(3 - elapsed)
        self._last_deepseek_call = datetime.now()
        if not self._deepseek_client:
            self._deepseek_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key,
                timeout=60.0,
                max_retries=0
            )
        extra_headers = {
            "HTTP-Referer": "https://skillsync.studio",
            "X-Title": "SkillSync Learning Platform"
        }
        kwargs = {
            "model": "deepseek/deepseek-chat-v3.1:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "extra_headers": extra_headers
        }
        response = await self._deepseek_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _generate_with_groq(self, prompt: str, max_tokens: int = 4096) -> str:
        try:
            from groq import AsyncGroq
        except Exception as ie:
            logger.warning("⚠️ groq client not available: %s", ie)
            raise RuntimeError("Groq client not available") from ie
        if not self._groq_client:
            self._groq_client = AsyncGroq(api_key=self.groq_api_key)
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens
        }
        response = await self._groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _generate_with_gemini(self, prompt: str, max_tokens: int = 4096) -> str:
        try:
            import google.generativeai as genai
        except Exception as ie:
            logger.warning("⚠️ google.generativeai client not available: %s", ie)
            raise RuntimeError("Gemini client not available") from ie
        from datetime import datetime
        import asyncio
        # Rate limiting: 15 req/min = 4 seconds per request (Gemini 2.0 Flash free tier)
        if self._last_gemini_call:
            elapsed = (datetime.now() - self._last_gemini_call).total_seconds()
            if elapsed < 4:
                await asyncio.sleep(4 - elapsed)
        self._last_gemini_call = datetime.now()
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        generation_config = {
            "temperature": 0.3,
            "max_output_tokens": max_tokens,
        }
        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        return response.text

    def _create_roadmap_prompt(self, user_profile: UserProfile, goal: LearningGoal) -> str:
        # (Prompt construction code as before, omitted for brevity)
        style_guidance = {
            'hands_on': 'Prioritize practical projects, coding exercises, labs, and interactive tutorials. Include 70% hands-on resources with specific project suggestions.',
            'video': 'Focus on video tutorials, recorded lectures, and visual demonstrations. Include 70% video-based resources with specific course recommendations.',
            'reading': 'Emphasize written documentation, articles, books, and text-based guides. Include 70% reading materials with specific book/article titles.',
            'interactive': 'Prioritize interactive courses, discussions, mentoring, and collaborative learning. Include 70% interactive resources with community engagement.',
            'mixed': 'Provide a balanced mix of videos (30%), hands-on projects (30%), reading materials (25%), and interactive content (15%).'
        }
        style_instruction = style_guidance.get(user_profile.learning_style, style_guidance['mixed'])
        industry_context = {
            'technology': 'Focus on current tech stacks, developer tools, programming languages, frameworks, and industry best practices.',
            'healthcare': 'Emphasize compliance, patient safety, medical protocols, and healthcare-specific technologies.',
            'finance': 'Include financial regulations, risk management, analytical tools, and industry compliance requirements.',
            'education': 'Focus on pedagogical approaches, educational technologies, curriculum development, and learning assessment.',
            'marketing': 'Emphasize digital marketing tools, analytics, consumer behavior, and campaign optimization.',
            'design': 'Include design principles, creative tools, user experience, and portfolio development.',
            'sales': 'Focus on sales methodologies, CRM systems, customer psychology, and performance metrics.',
        }
        industry_note = industry_context.get(user_profile.industry.lower(), 'Tailor content to be relevant for professional development in this industry.')
        time_mapping = {
            '1-2': 'micro-learning sessions (15-30 min daily)',
            '3-5': 'focused study sessions (45-90 min, 3-4 times/week)',
            '5-10': 'intensive learning blocks (2-3 hours, 4-5 times/week)',
            '10+': 'immersive learning (3+ hours daily)'
        }
        time_guidance = time_mapping.get(user_profile.time_commitment, 'moderate study sessions')
    # Note: callers will append a strict instruction to ensure total_duration is short and machine-friendly.
        return f"""You are an expert learning consultant and curriculum designer with 15+ years of experience in {user_profile.industry} industry training. Create a highly detailed, personalized learning roadmap that will transform this learner from their current level to their target proficiency.\n\nLEARNER PROFILE:\nRole: {user_profile.role} ({user_profile.career_stage} level)\nIndustry: {user_profile.industry}\nLearning Style: {user_profile.learning_style}\nWeekly Commitment: {user_profile.time_commitment} hours ({time_guidance})\n\nSPECIFIC LEARNING GOAL:\nSkill: {goal.skill_name}\nObjective: {goal.description}\nTarget Mastery: {goal.target_skill_level} level\nPriority: {goal.priority}/5 (higher = more urgent)\n\nINDUSTRY CONTEXT: {industry_note}\n\nLEARNING STYLE OPTIMIZATION: {style_instruction}\n\nCRITICAL REQUIREMENTS:\n1. Specificity: Provide exact resource names, tools, platforms, and websites\n2. Measurable Outcomes: Include specific skills/knowledge gained per step\n3. Industry Relevance: All content must align with {user_profile.industry} industry needs\n4. Time Optimization: Structure for {time_guidance}\n5. Progressive Difficulty: Each step builds logically on the previous one\n6. Real-world Application: Include practical projects and portfolio pieces\n\nRESOURCE QUALITY STANDARDS:\n- Only recommend resources that actually exist and are currently available\n- Prioritize well-rated, recent content (2020+)\n- Include mix of free and premium options\n- Specify exact course/book/tool names, not generic descriptions\n\nOUTPUT FORMAT (STRICT JSON):\n{{\n  \"skill_name\": \"{goal.skill_name}\",\n  \"description\": \"Compelling 2-sentence overview of the complete learning journey and career impact\",\n  \"total_duration\": \"realistic timeframe based on {user_profile.time_commitment} hours/week\",\n  \"difficulty_level\": \"{goal.target_skill_level}\",\n  \"steps\": [\n    {{\n      \"title\": \"Engaging step name that clearly states the milestone\",\n      \"description\": \"Detailed 3-4 sentence description of what learner will master, why it matters, and how it connects to their {user_profile.role} role\",\n      \"estimated_duration\": \"specific timeframe (e.g., '2 weeks at 5 hours/week')\",\n      \"difficulty\": \"beginner|intermediate|advanced\",\n      \"resources\": [\n        \"Exact resource name with author/platform (e.g., 'JavaScript: The Good Parts by Douglas Crockford')\",\n        \"Specific course title (e.g., 'React Complete Guide 2024 by Maximilian Schwarzmüller on Udemy')\",\n        \"Precise tool/website (e.g., 'CodePen.io for practice exercises')\"\n      ],\n      \"skills_covered\": [\n        \"Specific, measurable skill #1\",\n        \"Specific, measurable skill #2\",\n        \"Specific, measurable skill #3\"\n      ]\n    }}\n  ]\n}}\n\nVALIDATION CHECKLIST:\n- Each step has 3-5 specific, real resources\n- Skills covered are measurable and industry-relevant\n- Total duration matches weekly commitment\n- Resources match the {user_profile.learning_style} learning preference\n- Content progresses logically from {goal.target_skill_level} foundations to mastery\n- Industry context ({user_profile.industry}) is woven throughout\n\nCreate 4-6 progressive steps that will genuinely prepare this {user_profile.role} to excel with {goal.skill_name} in the {user_profile.industry} industry."""

# Fallback and parse helpers (unchanged)

# Create global hybrid roadmap service instance
hybrid_roadmap_service = HybridRoadmapService()
