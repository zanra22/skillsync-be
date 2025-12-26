# === Roadmap & Module Voting Mutations ===
import strawberry
from asgiref.sync import sync_to_async
from .models import Roadmap, Module
from .types import RoadmapType, ModuleType

@strawberry.type
class RoadmapVotingMutation:
    @strawberry.mutation
    async def vote_roadmap(
        self,
        info,
        roadmap_id: int,
        vote_type: str
    ) -> RoadmapType:
        roadmap = await sync_to_async(Roadmap.objects.get)(id=roadmap_id)
        if vote_type == 'upvote':
            roadmap.upvotes += 1
        elif vote_type == 'downvote':
            roadmap.downvotes += 1
        await sync_to_async(roadmap.save)()
        return roadmap

    @strawberry.mutation
    async def vote_module(
        self,
        info,
        module_id: int,
        vote_type: str
    ) -> ModuleType:
        module = await sync_to_async(Module.objects.get)(id=module_id)
        if vote_type == 'upvote':
            module.upvotes += 1
        elif vote_type == 'downvote':
            module.downvotes += 1
        await sync_to_async(module.save)()
        return module

# === Roadmap & Module Mutations ===
import strawberry
from typing import Optional, List
from asgiref.sync import sync_to_async
from .models import Roadmap, Module
from .types import RoadmapType, ModuleType

@strawberry.type
class RoadmapMutation:
    @strawberry.mutation
    async def create_roadmap(
        self,
        info,
        title: str,
        description: str,
        user_id: str,
        goal_id: str,
        difficulty_level: str = 'beginner',
        total_duration: str = '',
        user_profile_snapshot: Optional[dict] = None,
        ai_model_version: str = 'gemini-2.0-flash-exp',
        status: str = 'active',
        progress: Optional[dict] = None
    ) -> RoadmapType:
        roadmap = await sync_to_async(Roadmap.objects.create)(
            title=title,
            description=description,
            user_id=user_id,
            goal_id=goal_id,
            difficulty_level=difficulty_level,
            total_duration=total_duration,
            user_profile_snapshot=user_profile_snapshot or {},
            ai_model_version=ai_model_version,
            status=status,
            progress=progress or {}
        )
        return roadmap

    @strawberry.mutation
    async def create_module(
        self,
        info,
        roadmap_id: int,
        title: str,
        description: str = '',
        order: int = 1,
        estimated_duration: str = '',
        difficulty: str = 'beginner',
        resources: Optional[List[str]] = None
    ) -> ModuleType:
        roadmap = await sync_to_async(Roadmap.objects.get)(id=roadmap_id)
        module = await sync_to_async(Module.objects.create)(
            roadmap=roadmap,
            title=title,
            description=description,
            order=order,
            estimated_duration=estimated_duration,
            difficulty=difficulty,
            resources=resources or []
        )
        return module
"""
Lessons GraphQL Mutations

This module provides GraphQL mutations for lesson management, voting, and regeneration.

Key Features:
- Community voting: Upvote/downvote lessons
- Lesson regeneration: Create new versions
- Mentor reviews: Professional verification

Author: SkillSync Team
Date: October 9, 2025
"""

import strawberry
import logging
import secrets
from typing import Optional
from asgiref.sync import sync_to_async
from django.utils import timezone

from .models import LessonContent, LessonVote, MentorReview, LessonGenerationRequest
from .request_key_validator import RequestKeyValidator
from .types import (
    VoteLessonInput,
    VoteLessonPayload,
    RegenerateLessonInput,
    RegenerateLessonPayload,
    MentorReviewInput,
    MentorReviewPayload,
    LessonContentType
)
from helpers.ai_lesson_service import LessonGenerationService, LessonRequest

logger = logging.getLogger(__name__)


@strawberry.type
class LessonsMutation:
    """
    GraphQL mutations for lesson management.
    
    Features:
    - Voting: Community curation of lesson quality
    - Regeneration: Create new versions of lessons
    - Mentor Review: Professional verification
    """
    
    @strawberry.mutation
    async def vote_lesson(
        self,
        info,
        input: VoteLessonInput
    ) -> VoteLessonPayload:
        """
        Vote on lesson quality (upvote/downvote).
        
        This enables community curation - best lessons surface to the top!
        
        Features:
        - Users can upvote (good) or downvote (needs improvement)
        - Can update existing vote (change mind)
        - Can add optional comment (feedback)
        - Auto-approval: 10+ net votes + 80%+ approval = auto-approved
        
        Args:
            info: GraphQL context
            input: VoteLessonInput with:
                - lesson_id: Lesson to vote on
                - vote_type: 'upvote' or 'downvote'
                - comment: Optional feedback
        
        Returns:
            VoteLessonPayload with updated lesson
        
        Example:
            mutation {
                lessons {
                    voteLesson(input: {
                        lessonId: 123,
                        voteType: "upvote",
                        comment: "Great explanation!"
                    }) {
                        success
                        message
                        lesson {
                            id
                            upvotes
                            downvotes
                        }
                    }
                }
            }
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            return VoteLessonPayload(
                success=False,
                message="Authentication required to vote",
                lesson=None
            )
        
        # Validate vote type
        if input.vote_type not in ['upvote', 'downvote']:
            return VoteLessonPayload(
                success=False,
                message=f"Invalid vote type: {input.vote_type}. Must be 'upvote' or 'downvote'",
                lesson=None
            )
        
        try:
            # Get lesson
            lesson = await sync_to_async(
                LessonContent.objects.get
            )(id=input.lesson_id)
            
            logger.info(f"🗳️ Vote from {user.email} on lesson {lesson.id}")
            
            # Check if user already voted
            existing_vote = await sync_to_async(
                lambda: LessonVote.objects.filter(
                    user=user,
                    lesson_content=lesson
                ).first()
            )()
            
            if existing_vote:
                # Update existing vote
                old_vote = existing_vote.vote_type
                
                logger.info(f"   Updating existing vote: {old_vote} → {input.vote_type}")
                
                # Remove old vote counts
                if old_vote == 'upvote':
                    lesson.upvotes -= 1
                elif old_vote == 'downvote':
                    lesson.downvotes -= 1
                
                # Update vote
                existing_vote.vote_type = input.vote_type
                existing_vote.comment = input.comment or ""
                existing_vote.updated_at = timezone.now()
                await sync_to_async(existing_vote.save)()
            else:
                # Create new vote
                logger.info(f"   New vote: {input.vote_type}")
                
                await sync_to_async(LessonVote.objects.create)(
                    user=user,
                    lesson_content=lesson,
                    vote_type=input.vote_type,
                    comment=input.comment or ""
                )
            
            # Add new vote counts
            if input.vote_type == 'upvote':
                lesson.upvotes += 1
            elif input.vote_type == 'downvote':
                lesson.downvotes += 1
            
            # Calculate approval rate
            total_votes = lesson.upvotes + lesson.downvotes
            approval_rate = (lesson.upvotes / total_votes * 100) if total_votes > 0 else 0
            
            # Auto-approve if quality threshold met
            net_votes = lesson.upvotes - lesson.downvotes
            if net_votes >= 10 and approval_rate >= 80:
                if lesson.approval_status == 'pending':
                    lesson.approval_status = 'approved'
                    logger.info(f"   🎉 Lesson auto-approved! ({net_votes} net votes, {approval_rate:.1f}% approval)")
            
            await sync_to_async(lesson.save)()
            
            logger.info(f"✅ Vote recorded: {lesson.upvotes} up, {lesson.downvotes} down")
            
            return VoteLessonPayload(
                success=True,
                message=f"Voted {input.vote_type} successfully",
                lesson=lesson
            )
            
        except LessonContent.DoesNotExist:
            logger.warning(f"⚠️ Lesson not found: ID {input.lesson_id}")
            return VoteLessonPayload(
                success=False,
                message=f"Lesson not found: ID {input.lesson_id}",
                lesson=None
            )
        except Exception as e:
            logger.error(f"❌ Vote failed: {e}", exc_info=True)
            return VoteLessonPayload(
                success=False,
                message=f"Failed to record vote: {str(e)}",
                lesson=None
            )
    
    @strawberry.mutation
    async def regenerate_lesson(
        self,
        info,
        input: RegenerateLessonInput
    ) -> RegenerateLessonPayload:
        """
        Generate a new version of an existing lesson.
        
        Use cases:
        - Lesson outdated (technology changed)
        - User wants different explanation style
        - Community feedback suggests improvements
        
        The new version will:
        - Have the same cache_key (so it's findable)
        - Start with 0 votes (compete with existing versions)
        - Be available as alternative version
        
        Args:
            info: GraphQL context
            input: RegenerateLessonInput with:
                - lesson_id: Lesson to regenerate
        
        Returns:
            RegenerateLessonPayload with old and new lessons
        
        Example:
            mutation {
                lessons {
                    regenerateLesson(input: {
                        lessonId: 123
                    }) {
                        success
                        message
                        oldLesson { id upvotes }
                        newLesson { id }
                    }
                }
            }
        """
        user = info.context.request.user
        
        try:
            # Get old lesson
            old_lesson = await sync_to_async(
                LessonContent.objects.get
            )(id=input.lesson_id)
            
            logger.info(f"🔄 Regenerating lesson {old_lesson.id}: '{old_lesson.title}'")
            
            # Generate new version
            lesson_service = LessonGenerationService()
            
            # Get user profile if available
            user_profile = None
            if user.is_authenticated and hasattr(user, 'profile'):
                try:
                    user_profile = await sync_to_async(lambda: user.profile)()
                except Exception:
                    pass
            
            new_lesson_data = lesson_service.generate_lesson(
                LessonRequest(
                    step_title=old_lesson.roadmap_step_title,
                    lesson_number=old_lesson.lesson_number,
                    learning_style=old_lesson.learning_style,
                    difficulty=old_lesson.difficulty_level,
                    user_profile=user_profile
                )
            )
            
            if not new_lesson_data:
                logger.error(f"❌ Regeneration failed: AI returned no data")
                return RegenerateLessonPayload(
                    success=False,
                    message="Failed to regenerate: AI service returned no data",
                    old_lesson=old_lesson,
                    new_lesson=None
                )
            
            logger.info(f"✅ AI generation complete, saving new version...")

            # Build generation metadata (stored in JSONB - no MongoDB needed!)
            generation_metadata = {
                'prompt': 'Regenerate lesson with improved quality',
                'model': 'gemini-2.0-flash-exp',
                'learning_style': old_lesson.learning_style,
                'difficulty': old_lesson.difficulty_level,
                'temperature': 0.7,
                'max_tokens': 2048,
                'generated_at': timezone.now().isoformat(),
                'ai_provider': 'gemini',
                'generation_attempt': 1,
                'regenerated_from': old_lesson.id
            }

            # Save as new version (SAME cache_key!)
            new_lesson = await sync_to_async(LessonContent.objects.create)(
                roadmap_step_title=old_lesson.roadmap_step_title,
                lesson_number=old_lesson.lesson_number,
                learning_style=old_lesson.learning_style,
                content=new_lesson_data,
                title=new_lesson_data.get('title', old_lesson.title),
                description=new_lesson_data.get('description', old_lesson.description),
                estimated_duration=new_lesson_data.get('estimated_duration', old_lesson.estimated_duration),
                difficulty_level=new_lesson_data.get('difficulty', old_lesson.difficulty_level),
                cache_key=old_lesson.cache_key,  # ← SAME cache_key (so it's findable)
                created_by='gemini-ai',
                ai_model_version='gemini-2.0-flash-exp',
                generated_by=user if user.is_authenticated else None,
                approval_status='pending',  # Needs community review
                upvotes=0,  # Start fresh
                downvotes=0,
                generation_metadata=generation_metadata  # ← Store all metadata in JSONB
            )
            
            logger.info(f"✅ New version created: Old {old_lesson.id} → New {new_lesson.id}")
            logger.info(f"   Both versions available (same cache_key: {old_lesson.cache_key})")
            
            return RegenerateLessonPayload(
                success=True,
                message=f"New lesson version created (ID: {new_lesson.id})",
                old_lesson=old_lesson,
                new_lesson=new_lesson
            )
            
        except LessonContent.DoesNotExist:
            logger.warning(f"⚠️ Lesson not found: ID {input.lesson_id}")
            return RegenerateLessonPayload(
                success=False,
                message=f"Lesson not found: ID {input.lesson_id}",
                old_lesson=None,
                new_lesson=None
            )
        except Exception as e:
            logger.error(f"❌ Regeneration failed: {e}", exc_info=True)
            return RegenerateLessonPayload(
                success=False,
                message=f"Failed to regenerate: {str(e)}",
                old_lesson=None,
                new_lesson=None
            )
    
    @strawberry.mutation
    async def mentor_review_lesson(
        self,
        info,
        input: MentorReviewInput
    ) -> MentorReviewPayload:
        """
        Mentor reviews a lesson (professional verification).
        
        Mentor reviews carry more weight than community votes.
        Verified lessons get priority in recommendations.
        
        Only mentors can call this mutation.
        
        Args:
            info: GraphQL context
            input: MentorReviewInput with:
                - lesson_id: Lesson to review
                - status: 'verified', 'needs_improvement', 'rejected'
                - feedback: Review comments
                - expertise_area: Mentor's area of expertise
        
        Returns:
            MentorReviewPayload with review and updated lesson
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            return MentorReviewPayload(
                success=False,
                message="Authentication required",
                review=None,
                lesson=None
            )
        
        # Check if user is mentor
        user_role = getattr(user, 'role', 'learner')
        if user_role != 'mentor':
            return MentorReviewPayload(
                success=False,
                message="Only mentors can review lessons",
                review=None,
                lesson=None
            )
        
        # Validate status
        valid_statuses = ['verified', 'needs_improvement', 'rejected']
        if input.status not in valid_statuses:
            return MentorReviewPayload(
                success=False,
                message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                review=None,
                lesson=None
            )
        
        try:
            # Get lesson
            lesson = await sync_to_async(
                LessonContent.objects.get
            )(id=input.lesson_id)
            
            logger.info(f"👨‍🏫 Mentor review from {user.email} on lesson {lesson.id}")
            logger.info(f"   Status: {input.status}")
            
            # Create review
            review = await sync_to_async(MentorReview.objects.create)(
                mentor=user,
                lesson_content=lesson,
                status=input.status,
                feedback=input.feedback,
                expertise_area=input.expertise_area
            )
            
            # Update lesson approval status if verified
            if input.status == 'verified':
                lesson.approval_status = 'mentor_verified'
                logger.info(f"   🎉 Lesson mentor-verified!")
            elif input.status == 'rejected':
                lesson.approval_status = 'rejected'
                logger.info(f"   ❌ Lesson rejected by mentor")
            
            await sync_to_async(lesson.save)()
            
            logger.info(f"✅ Mentor review recorded")
            
            return MentorReviewPayload(
                success=True,
                message=f"Lesson review recorded: {input.status}",
                review=review,
                lesson=lesson
            )
            
        except LessonContent.DoesNotExist:
            logger.warning(f"⚠️ Lesson not found: ID {input.lesson_id}")
            return MentorReviewPayload(
                success=False,
                message=f"Lesson not found: ID {input.lesson_id}",
                review=None,
                lesson=None
            )
        except Exception as e:
            logger.error(f"❌ Mentor review failed: {e}", exc_info=True)
            return MentorReviewPayload(
                success=False,
                message=f"Failed to record review: {str(e)}",
                review=None,
                lesson=None
            )


    @strawberry.mutation
    async def generate_module_lessons(
        self,
        info,
        module_id: str
    ) -> ModuleType:
        """
        Generate lessons for a module on-demand (when user clicks module).

        This is the RECOMMENDED approach for cost efficiency:
        - Only generates lessons when user actually views the module
        - Saves 60-80% on AI costs vs generating all lessons upfront
        - Provides better UX (fast dashboard load, lessons load when needed)

        Status flow:
        - not_started → queued → in_progress → completed/failed

        Security:
        - Generates unique one-time request key (like OTP)
        - Key is stored in database and passed to Azure Function
        - Azure Function returns key in request headers to Django for validation
        - Key is deleted after validation (single-use only)

        Args:
            info: GraphQL context
            module_id: Module ID to generate lessons for

        Returns:
            ModuleType with updated generation status

        Example:
            mutation {
                lessons {
                    generateModuleLessons(moduleId: "abc123") {
                        id
                        title
                        generationStatus
                        generationError
                    }
                }
            }
        """
        user = info.context.request.user
        request = info.context.request

        try:
            # ============================================
            # STEP 0: Check for Azure Function request key FIRST
            # ============================================
            # Azure Function includes one-time request key for service-to-service auth
            request_key_from_headers = RequestKeyValidator.get_request_key_from_headers(request)
            user_id_from_headers = RequestKeyValidator.get_user_id_from_headers(request)

            verified_user_id = None  # Track which user (from auth or headers)

            if request_key_from_headers:
                # This is a request from Azure Function (service-to-service)
                logger.info(f"🔑 [Validation] Azure Function request detected (has request key in headers)")
                logger.info(f"   Validating request key...")

                try:
                    # Validate the request key (will raise if invalid)
                    await RequestKeyValidator.validate_request_key(
                        request_key=request_key_from_headers,
                        user_id=user_id_from_headers,
                        module_id=module_id
                    )
                    logger.info(f"✅ [Validation] Request key validated successfully")
                    # Use user_id from headers for authenticated service requests
                    verified_user_id = user_id_from_headers
                except Exception as validation_error:
                    logger.error(f"❌ [Validation] Request key validation failed: {validation_error}")
                    raise Exception(f"Request key validation failed: {str(validation_error)}")
            else:
                # Regular user request from frontend - enforce authentication
                if not user.is_authenticated:
                    raise Exception("Authentication required")

                logger.debug(f"👤 Regular user request (no request key in headers)")
                # Use authenticated user's ID
                verified_user_id = str(user.id)

            # Get module with ownership verification (single efficient query)
            module = await Module.objects.select_related('roadmap').filter(
                id=module_id,
                roadmap__user_id=verified_user_id  # ✅ Verify user owns this module (from either auth or headers)
            ).afirst()

            if not module:
                raise Exception(f"Module not found or you don't have permission to access it")

            # Check if already generated/in-progress
            if module.generation_status in ['completed', 'in_progress']:
                logger.info(f"📦 Module {module_id} already {module.generation_status}, skipping")
                return module

            logger.info(f"🚀 On-demand generation requested for module: {module.title}")

            # ============================================
            # CRITICAL LOGIC SPLIT
            # ============================================
            # Two different flows based on request source:
            #
            # FLOW 1: Regular user request (no request key in headers)
            #   - Frontend calls mutation with JWT auth
            #   - Generate request key
            #   - Enqueue to Azure Service Bus
            #   - Return immediately (async processing)
            #   - Azure Function picks up message and calls back with request key
            #
            # FLOW 2: Azure Function request (has request key in headers)
            #   - Azure Function already validated request key
            #   - Skip enqueue (prevents duplicate work)
            #   - Directly generate lessons synchronously
            #   - Update module status to completed
            #   - Return generated module

            if request_key_from_headers:
                # ============================================
                # FLOW 2: Azure Function Callback (Direct Generation)
                # ============================================
                logger.info(f"🚀 [Azure] Direct lesson generation (request key validated)")

                # Import here to avoid circular dependency
                from helpers.ai_lesson_service import LessonGenerationService

                try:
                    # Update status to in_progress
                    module.generation_status = 'in_progress'
                    module.generation_started_at = timezone.now()
                    await module.asave()
                    logger.info(f"✅ Module status updated to 'in_progress'")

                    # Get user profile for personalization
                    user_profile = None
                    try:
                        # Get the actual user object from verified_user_id
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        actual_user = await User.objects.aget(id=verified_user_id)
                        if hasattr(actual_user, 'profile'):
                            user_profile = await sync_to_async(lambda: actual_user.profile)()
                    except Exception as profile_error:
                        logger.debug(f"Could not load user profile: {profile_error}")
                        pass

                    # Directly generate lessons
                    lesson_service = LessonGenerationService()
                    try:
                        lesson_count = await lesson_service.generate_lessons_for_module(
                            module=module,
                            user_profile=user_profile
                        )
                        logger.info(f"✅ Generated {lesson_count} lessons for module")

                        # CRITICAL: Check that lessons were actually created
                        if lesson_count == 0:
                            logger.error(f"❌ Lesson generation returned 0 lessons - marking as failed")
                            module.generation_status = 'failed'
                            module.generation_error = "Lesson generation failed: No lessons were created"
                            module.generation_completed_at = timezone.now()
                            await module.asave()
                            raise Exception("Lesson generation failed: No lessons were created")

                        # Update status to completed
                        module.generation_status = 'completed'
                        module.generation_completed_at = timezone.now()
                        module.generation_error = None
                        await module.asave()
                        logger.info(f"✅ Module status updated to 'completed'")

                    finally:
                        await lesson_service.cleanup()

                except Exception as generation_error:
                    logger.error(f"❌ Direct lesson generation failed: {generation_error}", exc_info=True)
                    module.generation_status = 'failed'
                    module.generation_error = str(generation_error)[:500]
                    module.generation_completed_at = timezone.now()
                    await module.asave()
                    raise Exception(f"Lesson generation failed: {str(generation_error)}")

                # Refresh and return
                await module.arefresh_from_db()
                return module

            else:
                # ============================================
                # FLOW 1: Regular User Request (Queue for Azure)
                # ============================================
                logger.info(f"📋 [Frontend] Queueing module for async generation")

                # Generate unique one-time request key
                request_key = secrets.token_urlsafe(32)
                logger.info(f"🔑 Generated request key for secure authentication")

                # Save key to database (will be deleted after validation)
                # Use verified_user_id (from either auth or headers) instead of user.id
                # This ensures the key matches the user who triggered the request
                await sync_to_async(LessonGenerationRequest.objects.create)(
                    module_id=module_id,
                    user_id=verified_user_id,  # ← Use verified_user_id, not user.id
                    request_key=request_key
                )
                logger.debug(f"   Key stored in database for validation")

                # Get user profile for personalization
                user_profile = None
                try:
                    # Use sync_to_async to check profile in async context
                    has_profile = await sync_to_async(lambda: hasattr(user, 'profile'))()
                    if has_profile:
                        user_profile = await sync_to_async(lambda: user.profile)()
                except Exception as profile_error:
                    logger.debug(f"Could not load user profile: {profile_error}")
                    pass

                # Import here to avoid circular dependency
                from helpers.ai_roadmap_service import HybridRoadmapService

                # ============================================
                # STEP 2: Enqueue for generation via Azure Service Bus
                # ============================================
                roadmap_service = HybridRoadmapService()
                try:
                    await roadmap_service.enqueue_module_for_generation(
                        module,
                        user_profile,
                        request_key=request_key  # ← Include key in message
                    )
                    logger.info(f"✅ Module queued for generation: {module.title}")
                finally:
                    # Cleanup async resources (critical on Windows)
                    await roadmap_service.cleanup()

                # Refresh module to get updated status
                await module.arefresh_from_db()

        except Exception as e:
            logger.error(f"❌ Failed to generate module lessons: {e}", exc_info=True)
            raise Exception(f"Failed to generate module lessons: {str(e)}")
    
    @strawberry.mutation
    async def generate_lesson_content(
        self,
        info,
        lesson_id: str
    ) -> LessonContentType:
        """
        Generate full content for a single lesson skeleton (ON-DEMAND).
        
        PHASE 2: ON-DEMAND GENERATION
        
        This mutation generates content for a lesson that has generation_status='pending'.
        It's called when a user clicks on a lesson to view it.
        
        Flow:
        1. Validates user has access to the lesson
        2. Calls LessonGenerationService.generate_single_lesson_content()
        3. Returns the updated lesson with full content
        
        Args:
            lesson_id: ID of the lesson to generate content for
        
        Returns:
            LessonContentType with generated content
        
        Example:
            mutation {
                generateLessonContent(lessonId: "abc123") {
                    id
                    title
                    generationStatus
                    content
                }
            }
        """
        from lessons.models import LessonContent
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        request = info.context.request
        
        # Support both JWT authentication and Azure Function X-User-Id header
        user = request.user
        user_id_from_header = request.headers.get('X-User-Id')
        
        if user_id_from_header:
            # Azure Function request - use user ID from header
            logger.info(f"🎯 [Mutation] Azure Function request for lesson: {lesson_id}")
            try:
                user = await User.objects.aget(id=user_id_from_header)
                logger.info(f"   User from header: {user.email}")
            except User.DoesNotExist:
                raise Exception(f"User not found: {user_id_from_header}")
        elif not user.is_authenticated:
            # Regular request without authentication
            raise Exception("Authentication required")
        else:
            # Regular JWT authenticated request
            logger.info(f"🎯 [Mutation] Generate lesson content: {lesson_id} (user: {user.email})")
        
        try:
            # Fetch the lesson
            lesson = await sync_to_async(LessonContent.objects.select_related('module__roadmap').get)(id=lesson_id)
            
            # Verify user has access to this lesson
            if str(lesson.module.roadmap.user_id) != str(user.id):
                raise Exception("You don't have access to this lesson")
            
            # Generate content using service
            service = LessonGenerationService()
            try:
                success = await service.generate_single_lesson_content(lesson_id)
                
                if not success:
                    raise Exception("Lesson generation failed")
                
                # Refresh lesson from DB to get updated content
                await lesson.arefresh_from_db()
                
                logger.info(f"✅ Lesson content generated: {lesson_id}")
                return lesson
                
            finally:
                await service.cleanup()
        
        except LessonContent.DoesNotExist:
            logger.error(f"❌ Lesson not found: {lesson_id}")
            raise Exception(f"Lesson not found: {lesson_id}")
        except Exception as e:
            logger.error(f"❌ Failed to generate lesson content: {e}", exc_info=True)
            raise Exception(f"Failed to generate lesson content: {str(e)}")


    @strawberry.mutation
    async def generate_lesson_skeletons(
        self,
        info,
        module_id: str
    ) -> ModuleType:
        """
        FAILSAFE: Generate lesson skeletons for a module that has no lessons.
        
        This is a manual failsafe for when onboarding skeleton generation fails.
        Users can click a "Generate Lessons" button to trigger this.
        
        Args:
            info: GraphQL context
            module_id: Module ID to generate skeletons for
            
        Returns:
            ModuleType with lesson skeletons created
            
        Example:
            mutation {
                lessons {
                    generateLessonSkeletons(moduleId: "abc123") {
                        id
                        title
                        lessons {
                            id
                            title
                            generationStatus
                        }
                    }
                }
            }
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        try:
            # Get module with ownership verification
            module = await Module.objects.select_related('roadmap').filter(
                id=module_id,
                roadmap__user_id=str(user.id)
            ).afirst()
            
            if not module:
                raise Exception("Module not found or you don't have permission")
            
            # Check if module already has lessons
            lesson_count = await sync_to_async(module.lessons.count)()
            if lesson_count > 0:
                logger.info(f"✅ Module already has {lesson_count} lessons, skipping skeleton generation")
                return module
            
            logger.info(f"🚀 [Failsafe] Generating lesson skeletons for module: {module.title}")
            
            # Get user profile for personalization
            from helpers.ai_lesson_service import LessonGenerationService
            
            user_profile = {
                'learning_style': 'hands_on',
                'learning_pace': 'moderate',
                'time_commitment_hours': 5.0,
            }
            
            # Generate skeletons
            lesson_service = LessonGenerationService()
            try:
                skeleton_count = await lesson_service.generate_lessons_for_module(
                    module=module,
                    user_profile=user_profile
                )
                
                logger.info(f"✅ [Failsafe] Created {skeleton_count} lesson skeletons")
                
                if skeleton_count == 0:
                    raise Exception("Failed to create lesson skeletons")
                
                # Refresh module to get updated lessons
                await module.arefresh_from_db()
                return module
                
            finally:
                await lesson_service.cleanup()
        
        except Exception as e:
            logger.error(f"❌ [Failsafe] Failed to generate skeletons: {e}", exc_info=True)
            raise Exception(f"Failed to generate lesson skeletons: {str(e)}")


# Export for schema registration
__all__ = ['LessonsMutation']
