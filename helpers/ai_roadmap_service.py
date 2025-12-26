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
    # ✅ NEW: Additional personalization fields from onboarding
    first_name: Optional[str] = None  # For personalized greetings
    current_role: Optional[str] = None  # Current profession (e.g., "Software Engineer", "Teacher")
    transition_timeline: Optional[str] = None  # Career transition timeline (e.g., "Within 6 months")

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
        # Close OpenRouter client
        if getattr(self, '_openrouter_client', None):
            try:
                await self._openrouter_client.close()
                logger.debug("🧹 Closed OpenRouter client")
            except Exception:
                try:
                    self._openrouter_client.close()
                except Exception:
                    pass
            finally:
                self._openrouter_client = None

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
        # PHASE 2: Pass user_profile and learning_goal for context-aware title generation
        # Extract first learning goal from user_profile (LearningGoal dataclass, not LearningRoadmap)
        learning_goal = user_profile.goals[0] if user_profile and hasattr(user_profile, 'goals') and user_profile.goals else None
        ai_title = await self.generate_title_from_goal(goal_input, user_profile, learning_goal)
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

            # SKELETON GENERATION STRATEGY (Phase 1):
            # Create lesson skeletons immediately during onboarding
            # - User sees full roadmap structure instantly
            # - Lessons have status='pending' until user requests them
            # - Full content generated on-demand when user clicks lesson
            
            from helpers.ai_lesson_service import LessonGenerationService
            
            lesson_service = LessonGenerationService()
            
            # Convert user_profile to dict for lesson service
            profile_dict = {}
            if user_profile:
                if isinstance(user_profile, dict):
                    profile_dict = user_profile
                else:
                    # Extract relevant fields from user_profile object
                    profile_dict = {
                        'learning_style': getattr(user_profile, 'learning_style', 'hands_on'),
                        'learning_pace': getattr(user_profile, 'learning_pace', 'moderate'),
                        'time_commitment_hours': getattr(user_profile, 'time_commitment_hours', 5.0),
                    }
            
            # Generate lesson skeletons for this module with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    skeleton_count = await lesson_service.generate_lessons_for_module(
                        module=module_obj,
                        user_profile=profile_dict
                    )
                    logger.info(f"   ✅ Created {skeleton_count} lesson skeletons for: {module_obj.title}")
                    lessons_by_module[module_obj.title] = []  # Skeletons stored in DB, not returned here
                    break  # Success - exit retry loop
                except Exception as skeleton_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"   ⚠️ Attempt {attempt + 1} failed for {module_obj.title}: {skeleton_error}. Retrying...")
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                    else:
                        logger.error(f"   ❌ Failed to create skeletons for {module_obj.title} after {max_retries} attempts: {skeleton_error}")
                        lessons_by_module[module_obj.title] = []

        # Cleanup lesson service AFTER all modules are processed
        try:
            await lesson_service.cleanup()
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Lesson service cleanup error: {cleanup_error}")

        logger.info(f"[RoadmapSave] Modules created: {len(modules)}. Lesson skeletons created for on-demand generation.")
        return roadmap_obj, modules, lessons_by_module
    
    async def enqueue_module_for_generation(self, module_obj, user_profile, request_key=None):
        """
        Enqueue lessons for a module via Azure Service Bus.
        Called when user clicks "Generate" button to generate lessons for a specific module.

        Security:
        - request_key: One-time key for Azure Function authentication (generated by Django)
        - Azure Function includes this key in request headers to Django
        - Django validates key exists, belongs to user, and hasn't been used
        - Key is deleted after validation (single-use pattern, like OTP)
        """
        logger.info(f"📋 [Enqueue] Starting to enqueue module: {module_obj.title} (ID: {module_obj.id})")
        logger.info(f"📋 [Enqueue] Current module status: {module_obj.generation_status}")

        # Generate idempotency key to prevent duplicate processing
        idempotency_key = self._generate_idempotency_key(module_obj)
        logger.info(f"🔑 [Enqueue] Generated idempotency key: {idempotency_key}")

        # Update module with queued status and idempotency key
        module_obj.generation_status = 'queued'
        module_obj.idempotency_key = idempotency_key
        module_obj.generation_started_at = timezone.now()  # ✅ FIXED: Use timezone-aware datetime
        await module_obj.asave()
        logger.info(f"✅ [Enqueue] Module status updated to 'queued'")

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

        # Add request key for secure authentication (if provided)
        if request_key:
            message_data['request_key'] = request_key
            logger.debug(f"🔐 [Enqueue] Request key included in message for Azure Function authentication")

        logger.info(f"📦 [Enqueue] Prepared message data for queue")

        # Send message to Azure Service Bus (lesson-generation queue)
        logger.info(f"🚀 [Enqueue] Calling _send_to_service_bus...")
        await self._send_to_service_bus(message_data, 'lesson-generation')

        logger.info(f"✅ [Enqueue] Lessons queued for module '{module_obj.title}' with idempotency key: {idempotency_key}")
    
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
        logger.info(f"🔔 [ServiceBus] Starting to send message to queue '{queue_name}'")
        logger.info(f"📦 [ServiceBus] Message data: module_id={message_data.get('module_id')}, title={message_data.get('title')}")

        service_bus_conn_str = os.getenv('AZURE_SERVICE_BUS_CONNECTION_STRING')

        if not service_bus_conn_str:
            logger.error("❌ [ServiceBus] AZURE_SERVICE_BUS_CONNECTION_STRING not found in environment!")
            logger.error("❌ [ServiceBus] Available env vars: " + ", ".join([k for k in os.environ.keys() if 'AZURE' in k or 'SERVICE' in k]))
            # TODO: Implement direct processing fallback
            return

        # Debug: Log that we have the connection string (without exposing the full key)
        logger.info(f"✅ [ServiceBus] Found connection string (starts with: {service_bus_conn_str[:50]}...)")
        logger.info(f"🎯 [ServiceBus] Target queue: {queue_name}")

        try:
            logger.info(f"🔧 [ServiceBus] Creating ServiceBusClient...")
            # Create a Service Bus client
            service_bus_client = ServiceBusClient.from_connection_string(service_bus_conn_str)

            # ✅ FIXED: Use async context manager for async code
            async with service_bus_client:
                logger.info(f"📨 [ServiceBus] Getting queue sender for '{queue_name}'...")
                sender = service_bus_client.get_queue_sender(queue_name=queue_name)

                # Create a message with the serialized data
                logger.info(f"📝 [ServiceBus] Creating message with {len(json.dumps(message_data))} bytes...")
                message = ServiceBusMessage(json.dumps(message_data))

                # Send the message using async context
                logger.info(f"🚀 [ServiceBus] Sending message to queue...")
                async with sender:
                    await sender.send_messages(message)

            logger.info(f"✅ [ServiceBus] Message sent to queue '{queue_name}' successfully")
            logger.info(f"🎉 [ServiceBus] Module {message_data.get('module_id')} queued for lesson generation")
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

    async def generate_title_from_goal(
        self,
        goal_input: str,
        user_profile: Optional['UserProfile'] = None,
        learning_goal: Optional['LearningGoal'] = None
    ) -> str:
        """
        PHASE 2: Generate context-aware roadmap title using user profile and learning goal.

        Uses AI to create personalized titles that reflect:
        - Career stage (student, professional, career_changer)
        - Industry context
        - Target skill level
        - Time commitment/urgency

        Examples:
        - Student: "Python Fundamentals: 12-Week Beginner"
        - Professional: "Advanced Python for Finance"
        - Career Changer: "Python for Career Shifters: Finance→Tech"
        - Senior: "Python Advanced Patterns: Executive Track"

        Falls back to simple title if user_profile not provided.
        """
        # Fallback: If no user profile provided, use simple regex-based title
        if not user_profile or not learning_goal:
            import re
            keywords = re.findall(
                r'Python|JavaScript|Data Science|Career|Development|Beginner|Advanced',
                goal_input,
                re.IGNORECASE
            )
            if keywords:
                base = ' '.join(keywords)
                return f"{base.title()} Roadmap"
            return f"{goal_input.strip().title()} Roadmap"

        # PHASE 2: AI-powered context-aware title generation
        logger.info(f"🎯 Generating context-aware roadmap title for: {learning_goal.skill_name}")

        # Build context about the learner
        career_stage_desc = {
            'student': 'a student building foundational knowledge',
            'entry_level': 'an entry-level professional transitioning into the field',
            'mid_level': 'a mid-level professional expanding expertise',
            'senior_level': 'a senior professional adding specialized skills',
            'career_changer': 'a career changer transitioning from a different field',
            'executive': 'an executive or decision-maker upskilling',
        }.get(user_profile.career_stage, user_profile.career_stage)

        # ✅ PHASE 5: Build personalized greeting and transition context
        greeting = f"{user_profile.first_name}, " if user_profile.first_name else ""

        # Add career transition context for career changers
        transition_context = ""
        if user_profile.career_stage == 'career_changer' and user_profile.current_role:
            transition_context = f"\n- Current Role: {user_profile.current_role}"
            if user_profile.transition_timeline:
                transition_context += f"\n- Timeline: {user_profile.transition_timeline}"

        # Add professional context for working professionals
        professional_context = ""
        if user_profile.career_stage in ['mid_level', 'senior_level'] and user_profile.current_role:
            professional_context = f"\n- Current Position: {user_profile.current_role}"

        prompt = f"""Create a compelling, personalized roadmap title for {greeting}this learner.

Learner Context:
- Role: {career_stage_desc}
- Industry: {user_profile.industry}{transition_context}{professional_context}
- Learning Style: {user_profile.learning_style}
- Time Commitment: {user_profile.time_commitment} hours/week
- Target Level: {learning_goal.target_skill_level}

Learning Goal: Master {learning_goal.skill_name}

Generate a SINGLE title (not multiple) that:
1. Shows the learner's context (career stage, industry transition if applicable)
2. Indicates progression from their current state
3. Feels personalized and motivating
4. Is concise (under 70 characters if possible)
5. Includes the skill name ({learning_goal.skill_name})

Format: Just return the title text only, no quotes, no explanation.

Example formats:
- For students: "{learning_goal.skill_name} Fundamentals: [duration]"
- For professionals: "Advanced {learning_goal.skill_name} for [Industry]"
- For career changers: "{learning_goal.skill_name} for Career Shifters: [From]→[To]"
- For seniors: "{learning_goal.skill_name} Advanced: Executive Track"

Your title:"""

        try:
            # Try DeepSeek V3.1 first
            title = None
            if self.openrouter_api_key:
                try:
                    title = await self._generate_with_deepseek_v31(prompt, max_tokens=100)
                except Exception as e:
                    logger.warning(f"⚠️ DeepSeek V3.1 title generation failed: {e}")

            # Fallback to Groq
            if not title and self.groq_api_key:
                try:
                    title = await self._generate_with_groq(prompt, max_tokens=100)
                except Exception as e:
                    logger.warning(f"⚠️ Groq title generation failed: {e}")

            # Fallback to Gemini
            if not title and self.gemini_api_key:
                try:
                    title = await self._generate_with_gemini(prompt, max_tokens=100)
                except Exception as e:
                    logger.warning(f"⚠️ Gemini title generation failed: {e}")

            if not title:
                raise Exception("All AI providers failed")

            # Clean up the response
            title = title.strip().strip('"').strip("'")

            # Ensure it includes the skill name
            if learning_goal.skill_name.lower() not in title.lower():
                logger.warning(f"⚠️ Title missing skill name, appending it")
                title = f"{title}: {learning_goal.skill_name}"

            logger.info(f"✅ Context-aware title: {title}")
            return title

        except Exception as e:
            logger.warning(f"⚠️ AI title generation failed: {e}, falling back to simple title")
            # Fallback to simple title
            return f"{learning_goal.skill_name.title()}: {user_profile.career_stage.replace('_', ' ').title()} Roadmap"

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
            # Log the actual AI response for debugging
            logger.info(f"📝 AI Response (first 500 chars): {ai_text[:500] if ai_text else 'EMPTY/NONE'}")
            logger.info(f"📏 AI Response length: {len(ai_text) if ai_text else 0}")

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
                    logger.error(f"📋 Full AI Response: {ai_text}")
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
        self._openrouter_client = None
        self._last_deepseek_call = None
        self._last_gemini_call = None
        self._last_openrouter_call = None
        self._model_usage = {'qwen_coder': 0, 'groq': 0, 'gemini': 0}
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
        try:
            prompt = self._enforce_total_duration_prompt(prompt)
        except Exception:
            pass
            
        try:
            # PRIORITY 1: Groq Llama 3.3 70B (Fastest & Reliable)
            if self.groq_api_key:
                try:
                    logger.info("🚀 Primary: Trying Groq Llama 3.3 70B...")
                    content = await self._generate_with_groq(prompt)
                    self._model_usage['groq'] += 1
                    logger.info("✅ Groq API call success")
                    parsed_result = self._parse_ai_response(content, goal)
                    if parsed_result is None:
                        raise ValueError("Groq returned invalid/unparseable response")
                    logger.info("✅ Groq roadmap parsed successfully")
                    return parsed_result
                except Exception as e:
                    logger.warning(f"⚠️ Groq error: {e}, falling back to Gemini")

            # PRIORITY 2: Gemini 2.5 Flash (Stable Backup)
            if self.gemini_api_key:
                try:
                    logger.info("🔷 Secondary: Trying Gemini 2.5 Flash...")
                    content = await self._generate_with_gemini(prompt)
                    self._model_usage['gemini'] += 1
                    logger.info("✅ Gemini API call success")
                    parsed_result = self._parse_ai_response(content, goal)
                    if parsed_result is None:
                        raise ValueError("Gemini returned invalid/unparseable response")
                    logger.info("✅ Gemini roadmap parsed successfully")
                    return parsed_result
                except Exception as e:
                    logger.warning(f"⚠️ Gemini error: {e}, falling back to Qwen")

            # PRIORITY 3: Qwen 3 Coder (Fallback)
            if self.openrouter_api_key:
                try:
                    logger.info("🤖 Tertiary: Trying Qwen 3 Coder...")
                    content = await self._generate_with_openrouter(prompt, model="qwen/qwen3-coder:free")
                    self._model_usage['qwen_coder'] += 1
                    logger.info("✅ Qwen 3 Coder API call success")
                    parsed_result = self._parse_ai_response(content, goal)
                    if parsed_result is None:
                        raise ValueError("Qwen returned invalid/unparseable response")
                    logger.info("✅ Qwen roadmap parsed successfully")
                    return parsed_result
                except Exception as e:
                    logger.error(f"❌ Qwen 3 Coder error: {e}")

            logger.error("❌ All AI providers failed for roadmap generation")
            return None
        except Exception as e:
            logger.error(f"❌ Error in hybrid roadmap generation: {e}")
            return None

    async def _generate_with_openrouter(self, prompt: str, model: str = "qwen/qwen3-coder:free", max_tokens: int = 4096) -> str:
        try:
            from openai import AsyncOpenAI
        except Exception as ie:
            logger.warning("⚠️ openai/OpenRouter client not available: %s", ie)
            raise RuntimeError("OpenRouter client not available") from ie
        
        from datetime import datetime
        import asyncio
        
        # Simple rate limit for OpenRouter models
        # (Assuming generic 1s buffer if shared key usage)
        if self._last_openrouter_call:
            elapsed = (datetime.now() - self._last_openrouter_call).total_seconds()
            if elapsed < 1:
                await asyncio.sleep(1 - elapsed)
        self._last_openrouter_call = datetime.now()

        if not self._openrouter_client:
            self._openrouter_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key,
                timeout=60.0,
                max_retries=1
            )
            
        extra_headers = {
            "HTTP-Referer": "https://skillsync.studio",
            "X-Title": "SkillSync Learning Platform"
        }
        
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "extra_headers": extra_headers
        }
        
        response = await self._openrouter_client.chat.completions.create(**kwargs)
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
        # Rate limiting: 10 req/min = 6 seconds per request (Gemini 2.5 Flash free tier)
        if self._last_gemini_call:
            elapsed = (datetime.now() - self._last_gemini_call).total_seconds()
            if elapsed < 6:
                await asyncio.sleep(6 - elapsed)
        self._last_gemini_call = datetime.now()
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.3, "max_output_tokens": max_tokens}
        )
        response = await model.generate_content_async(prompt)
        return response.text

    def _calculate_module_count(
        self,
        target_skill_level: str,
        time_commitment: str,
        career_stage: str,
        learning_style: str
    ) -> str:
        """
        Calculate dynamic module count based on 5 factors.

        PHASE 2: Smart calculation replacing hardcoded "4-6 progressive steps"

        Factors:
        1. Target skill level (beginner → fewer, expert → more)
        2. Time commitment (1-3 hours → fewer, 10+ hours → more)
        3. Career stage (career_changer gets +20%)
        4. Learning style (hands_on → more modules, reading → fewer deeper ones)
        5. Total duration (estimated from time commitment and skill level)

        Returns: String like "4-6" or "5-7" to use in prompt
        """
        logger.info(f"📊 Calculating module count: {target_skill_level}, {time_commitment}h/week, {career_stage}, {learning_style}")

        # Base module count by skill level
        if target_skill_level.lower() == 'beginner':
            base_min, base_max = 4, 5
        elif target_skill_level.lower() == 'intermediate':
            base_min, base_max = 5, 7
        else:  # advanced or expert
            base_min, base_max = 6, 9

        # Duration factor (extracted from time_commitment string like "1-3", "5-10", "10+")
        duration_factor = 1.0
        try:
            # Extract number from time commitment (e.g., "1-3" → 2.5 avg, "5-10" → 7.5 avg)
            if "10+" in time_commitment:
                hours_per_week = 10
            elif "-" in time_commitment:
                parts = time_commitment.split("-")
                hours_per_week = (int(parts[0]) + int(parts[1])) / 2
            else:
                hours_per_week = int(time_commitment) if time_commitment.isdigit() else 5

            # Adjust based on hours per week
            if hours_per_week <= 3:
                duration_factor = 0.7  # Quick learners: fewer modules
            elif hours_per_week <= 5:
                duration_factor = 0.9
            elif hours_per_week <= 10:
                duration_factor = 1.0  # Normal pace
            else:
                duration_factor = 1.2  # Intensive learners: more modules
        except Exception as e:
            logger.debug(f"Could not parse time commitment '{time_commitment}': {e}")
            duration_factor = 1.0

        # Career stage factor
        career_factor = 1.0
        if career_stage and 'changer' in career_stage.lower():
            career_factor = 1.2  # Career changers need more comprehensive foundation
        elif career_stage and 'student' in career_stage.lower():
            career_factor = 1.0
        elif career_stage and ('senior' in career_stage.lower() or 'executive' in career_stage.lower()):
            career_factor = 0.85  # Senior professionals: focused modules only

        # Learning style factor
        style_factor = 1.0
        if learning_style and 'hands_on' in learning_style.lower():
            style_factor = 1.15  # More modules for practical focus
        elif learning_style and 'reading' in learning_style.lower():
            style_factor = 0.9  # Fewer, deeper modules for reading
        elif learning_style and 'video' in learning_style.lower():
            style_factor = 1.0  # Standard for video
        else:  # mixed
            style_factor = 1.0

        # Calculate final count
        min_count = int(base_min * duration_factor * career_factor * style_factor)
        max_count = int(base_max * duration_factor * career_factor * style_factor)

        # Enforce reasonable bounds
        min_count = max(2, min(min_count, 12))
        max_count = max(min_count + 1, min(max_count, 14))

        result = f"{min_count}-{max_count}"
        logger.info(f"✅ Dynamic module count: {result} (base: {base_min}-{base_max}, duration: {duration_factor}, career: {career_factor}, style: {style_factor})")

        return result

    def _create_roadmap_prompt(self, user_profile: UserProfile, goal: LearningGoal) -> str:
        """
        Create prompt for roadmap generation with dynamic module count.

        PHASE 2: Uses _calculate_module_count() instead of hardcoded "4-6"
        """
        # PHASE 2: Calculate dynamic module count
        module_count = self._calculate_module_count(
            target_skill_level=goal.target_skill_level,
            time_commitment=user_profile.time_commitment,
            career_stage=user_profile.career_stage,
            learning_style=user_profile.learning_style
        )

        # (Prompt construction code as before)
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

        # ✅ PHASE 5: Build role-specific context sections
        personalized_greeting = f"Hello {user_profile.first_name}! " if user_profile.first_name else ""

        # Career transition context (for career changers only)
        career_transition_section = ""
        if user_profile.career_stage == 'career_changer' and user_profile.current_role and user_profile.transition_timeline:
            career_transition_section = f"""
CAREER TRANSITION CONTEXT:
Current Role: {user_profile.current_role}
Target Field: {user_profile.industry}
Timeline: {user_profile.transition_timeline}
CRITICAL: This learner is transitioning careers. Focus on:
- Transferable skills from {user_profile.current_role} to {user_profile.industry}
- Portfolio-building projects that demonstrate career readiness
- Industry-specific terminology and professional practices
- Networking opportunities and community engagement
- Job search preparation and interview skills for {user_profile.industry} roles
"""

        # Professional context (for working professionals)
        professional_section = ""
        if user_profile.career_stage in ['mid_level', 'senior_level'] and user_profile.current_role:
            professional_section = f"""
PROFESSIONAL CONTEXT:
Current Position: {user_profile.current_role}
Career Level: {user_profile.career_stage}
FOCUS: This is an experienced professional upskilling. Emphasize:
- Advanced concepts and best practices relevant to {user_profile.current_role}
- Leadership and mentorship opportunities
- Cutting-edge industry trends and emerging technologies
- Strategic application to current role responsibilities
- Time-efficient learning (respect their professional commitments)
"""

        # Student context (for students)
        student_section = ""
        if user_profile.career_stage == 'student':
            student_section = f"""
STUDENT CONTEXT:
Career Stage: Student / Early Learner
FOCUS: Building strong foundations for career entry. Emphasize:
- Comprehensive fundamentals with clear explanations
- Hands-on projects for portfolio building
- Interview preparation and technical assessment practice
- Career guidance and industry insights
- Community resources and peer learning opportunities
"""

        # Combine role-specific sections
        role_specific_context = career_transition_section + professional_section + student_section

        # Note: callers will append a strict instruction to ensure total_duration is short and machine-friendly.
        return f"""{personalized_greeting}You are an expert learning consultant and curriculum designer with 15+ years of experience in {user_profile.industry} industry training. Create a highly detailed, personalized learning roadmap that will transform this learner from their current level to their target proficiency.\n\nLEARNER PROFILE:\nRole: {user_profile.role} ({user_profile.career_stage} level)\nIndustry: {user_profile.industry}\nLearning Style: {user_profile.learning_style}\nWeekly Commitment: {user_profile.time_commitment} hours ({time_guidance}){role_specific_context}\n\nSPECIFIC LEARNING GOAL:\nSkill: {goal.skill_name}\nObjective: {goal.description}\nTarget Mastery: {goal.target_skill_level} level\nPriority: {goal.priority}/5 (higher = more urgent)\n\nINDUSTRY CONTEXT: {industry_note}\n\nLEARNING STYLE OPTIMIZATION: {style_instruction}\n\nMODULE NAMING CONVENTION (PHASE 2 - CONTEXT-AWARE):\nEach step represents a module. Create titles that:\n1. Show the learner's context: industry, role, career transition\n2. Progress from {goal.target_skill_level} → advanced\n3. Be specific and actionable (not generic)\n4. Include domain terms from {user_profile.industry} when applicable\n5. Reference practical application in their field\n\nExamples for {goal.skill_name} in {user_profile.industry}:\n- Instead of: \"Introduction to Basics\"\n- Use: \"Foundations for {user_profile.industry} Professionals\"\n- Or: \"{goal.skill_name} in {user_profile.industry}: Setup & Environment\"\n- Or: \"From {{current_knowledge}} to {goal.skill_name}: Practical Application\"\n\nCRITICAL REQUIREMENTS:\n1. Specificity: Provide exact resource names, tools, platforms, and websites\n2. Measurable Outcomes: Include specific skills/knowledge gained per step\n3. Industry Relevance: All content must align with {user_profile.industry} industry needs\n4. Time Optimization: Structure for {time_guidance}\n5. Progressive Difficulty: Each step builds logically on the previous one\n6. Real-world Application: Include practical projects and portfolio pieces\n\nRESOURCE QUALITY STANDARDS:\n- Only recommend resources that actually exist and are currently available\n- Prioritize well-rated, recent content (2020+)\n- Include mix of free and premium options\n- Specify exact course/book/tool names, not generic descriptions\n\nOUTPUT FORMAT (STRICT JSON):\n{{\n  \"skill_name\": \"{goal.skill_name}\",\n  \"description\": \"Compelling 2-sentence overview of the complete learning journey and career impact\",\n  \"total_duration\": \"realistic timeframe based on {user_profile.time_commitment} hours/week\",\n  \"difficulty_level\": \"{goal.target_skill_level}\",\n  \"steps\": [\n    {{\n      \"title\": \"Engaging step name that clearly states the milestone\",\n      \"description\": \"Detailed 3-4 sentence description of what learner will master, why it matters, and how it connects to their {user_profile.role} role\",\n      \"estimated_duration\": \"specific timeframe (e.g., '2 weeks at 5 hours/week')\",\n      \"difficulty\": \"beginner|intermediate|advanced\",\n      \"resources\": [\n        \"Exact resource name with author/platform (e.g., 'JavaScript: The Good Parts by Douglas Crockford')\",\n        \"Specific course title (e.g., 'React Complete Guide 2024 by Maximilian Schwarzmüller on Udemy')\",\n        \"Precise tool/website (e.g., 'CodePen.io for practice exercises')\"\n      ],\n      \"skills_covered\": [\n        \"Specific, measurable skill #1\",\n        \"Specific, measurable skill #2\",\n        \"Specific, measurable skill #3\"\n      ]\n    }}\n  ]\n}}\n\nVALIDATION CHECKLIST:\n- Each step has 3-5 specific, real resources\n- Skills covered are measurable and industry-relevant\n- Total duration matches weekly commitment\n- Resources match the {user_profile.learning_style} learning preference\n- Content progresses logically from {goal.target_skill_level} foundations to mastery\n- Industry context ({user_profile.industry}) is woven throughout\n\nCreate {module_count} progressive steps that will genuinely prepare this {user_profile.role} to excel with {goal.skill_name} in the {user_profile.industry} industry."""

# Fallback and parse helpers (unchanged)

# Create global hybrid roadmap service instance
hybrid_roadmap_service = HybridRoadmapService()
