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
    MentorReviewPayload
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

        if not user.is_authenticated:
            raise Exception("Authentication required")

        try:
            # ============================================
            # STEP 0: Check for Azure Function request key
            # ============================================
            # Azure Function includes one-time request key for service-to-service auth
            request_key_from_headers = RequestKeyValidator.get_request_key_from_headers(request)
            user_id_from_headers = RequestKeyValidator.get_user_id_from_headers(request)

            if request_key_from_headers:
                # This is a request from Azure Function (service-to-service)
                logger.info(f"🔑 [Validation] Azure Function request detected (has request key in headers)")
                logger.info(f"   Validating request key...")

                try:
                    # Validate the request key
                    await RequestKeyValidator.validate_request_key(
                        request_key=request_key_from_headers,
                        user_id=user_id_from_headers or str(user.id),
                        module_id=module_id
                    )
                    logger.info(f"✅ [Validation] Request key validated successfully")
                except Exception as validation_error:
                    logger.error(f"❌ [Validation] Request key validation failed: {validation_error}")
                    raise Exception(f"Request key validation failed: {str(validation_error)}")
            else:
                # Regular user request from frontend - normal auth applies
                logger.debug(f"👤 Regular user request (no request key in headers)")

            # Get module with ownership verification (single efficient query)
            module = await Module.objects.select_related('roadmap').filter(
                id=module_id,
                roadmap__user_id=str(user.id)  # ✅ Verify user owns this module
            ).afirst()

            if not module:
                raise Exception(f"Module not found or you don't have permission to access it")

            # Check if already generated/in-progress
            if module.generation_status in ['completed', 'in_progress']:
                logger.info(f"📦 Module {module_id} already {module.generation_status}, skipping")
                return module

            logger.info(f"🚀 On-demand generation requested for module: {module.title}")

            # ============================================
            # STEP 1: Generate unique one-time request key
            # ============================================
            request_key = secrets.token_urlsafe(32)
            logger.info(f"🔑 Generated request key for secure authentication")

            # Save key to database (will be deleted after validation)
            await sync_to_async(LessonGenerationRequest.objects.create)(
                module_id=module_id,
                user_id=str(user.id),
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

            return module

        except Exception as e:
            logger.error(f"❌ Failed to generate module lessons: {e}", exc_info=True)
            raise Exception(f"Failed to generate module lessons: {str(e)}")


# Export for schema registration
__all__ = ['LessonsMutation']
