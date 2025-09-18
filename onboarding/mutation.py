import strawberry
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from typing import Optional
from asgiref.sync import sync_to_async
from profiles.models import UserIndustry, UserLearningGoal
from profiles.choices import IndustryType, SkillLevel, CareerStage
from helpers.ai_roadmap_service import gemini_ai_service, UserProfile as AIUserProfile, LearningGoal
from .types import (
    CompleteOnboardingInput, 
    CompleteOnboardingPayload, 
    OnboardingUser, 
    LearningRoadmap,
    RoadmapStep
)

logger = logging.getLogger(__name__)
User = get_user_model()


@strawberry.type
class OnboardingMutation:
    
    @strawberry.mutation
    async def complete_onboarding(
        self, 
        info, 
        input: CompleteOnboardingInput
    ) -> CompleteOnboardingPayload:
        """
        Complete user onboarding by updating profile and creating goals.
        """
        try:
            # Handle development mode user context
            dev_user_id = info.context.request.headers.get('X-Dev-User-ID')
            is_dev_mode = info.context.request.headers.get('X-Dev-Mode') == 'true'
            
            if is_dev_mode and dev_user_id:
                logger.info(f"🔧 Development mode: Using user ID {dev_user_id}")
                try:
                    user = await sync_to_async(User.objects.get)(id=dev_user_id)
                    logger.info(f"✅ Development mode: Found user {user.email}")
                except User.DoesNotExist:
                    logger.error(f"❌ Development mode: User {dev_user_id} not found")
                    return CompleteOnboardingPayload(
                        success=False,
                        message=f"Development user {dev_user_id} not found"
                    )
            else:
                # Check if user is authenticated (normal mode)
                if not info.context.request.user.is_authenticated:
                    return CompleteOnboardingPayload(
                        success=False,
                        message="Authentication required"
                    )
                user = info.context.request.user
            
            logger.info(f"🚀 Processing onboarding completion for user: {user.email}")
            
            # Update user role only (basic auth info stays in User model)
            user.role = input.role
            await sync_to_async(user.save)()
            
            # Get or create user profile and update personal information
            from profiles.models import UserProfile as DjangoUserProfile
            
            # Map career stage to choice value
            career_stage_mapping = {
                'student': CareerStage.STUDENT,
                'entry_level': CareerStage.ENTRY_LEVEL,
                'mid_level': CareerStage.MID_LEVEL,
                'senior_level': CareerStage.SENIOR_LEVEL,
                'executive': CareerStage.EXECUTIVE,
                'career_changer': CareerStage.CAREER_CHANGER,
                'freelancer': CareerStage.FREELANCER,
            }
            
            career_stage_choice = career_stage_mapping.get(
                input.career_stage.lower(),
                CareerStage.ENTRY_LEVEL
            )
            
            profile, created = await sync_to_async(
                DjangoUserProfile.objects.get_or_create
            )(
                user=user,
                defaults={
                    'first_name': input.first_name,
                    'last_name': input.last_name,
                    'bio': input.bio or '',
                    'career_stage': career_stage_choice,
                    'onboarding_completed': True,
                    'onboarding_step': 'complete'
                }
            )
            
            if not created:
                # Update existing profile
                profile.first_name = input.first_name
                profile.last_name = input.last_name
                profile.bio = input.bio or ''
                profile.career_stage = career_stage_choice
                profile.onboarding_completed = True
                profile.onboarding_step = 'complete'
                await sync_to_async(profile.save)()
            
            logger.info(f"✅ User profile updated: {user.email}")
            
            # Handle industry selection
            user_industry = None
            if input.industry:
                try:
                    # Map the industry name to the choice value
                    industry_mapping = {
                        'Technology': IndustryType.TECHNOLOGY,
                        'Healthcare': IndustryType.HEALTHCARE,
                        'Finance': IndustryType.FINANCE,
                        'Education': IndustryType.EDUCATION,
                        'Manufacturing': IndustryType.MANUFACTURING,
                        'Marketing': IndustryType.MARKETING,
                        'Design': IndustryType.DESIGN,
                        'Sales': IndustryType.SALES,
                        'Consulting': IndustryType.CONSULTING,
                        'Startup': IndustryType.STARTUP,
                        'Non-profit': IndustryType.NON_PROFIT,
                        'Government': IndustryType.GOVERNMENT,
                        'Other': IndustryType.OTHER,
                    }
                    
                    industry_choice = industry_mapping.get(input.industry, IndustryType.OTHER)
                    
                    user_industry, created = await sync_to_async(
                        UserIndustry.objects.get_or_create
                    )(
                        user=user,
                        industry=industry_choice,
                        defaults={'is_primary': True}
                    )
                    
                    if not created:
                        user_industry.is_primary = True
                        await sync_to_async(user_industry.save)()
                    
                    logger.info(f"✅ Industry updated: {input.industry} - {input.career_stage}")
                    
                except Exception as e:
                    logger.error(f"❌ Error updating industry: {e}")
                    # Create a default technology industry if there's an error
                    user_industry, _ = await sync_to_async(
                        UserIndustry.objects.get_or_create
                    )(
                        user=user,
                        industry=IndustryType.TECHNOLOGY,
                        defaults={'is_primary': True}
                    )
            
            # Handle learning goals
            created_goals = []
            if input.goals and user_industry:
                try:
                    # Clear existing goals for this industry
                    await sync_to_async(
                        UserLearningGoal.objects.filter(
                            user=user, 
                            industry=user_industry
                        ).delete
                    )()
                    
                    # Create new goals
                    for goal_input in input.goals:
                        # Map target skill level to choice value
                        skill_level_mapping = {
                            'beginner': SkillLevel.BEGINNER,
                            'intermediate': SkillLevel.INTERMEDIATE,
                            'advanced': SkillLevel.INTERMEDIATE,  # Map advanced to intermediate for now
                            'expert': SkillLevel.EXPERT,
                        }
                        
                        target_level = skill_level_mapping.get(
                            goal_input.target_skill_level.lower(),
                            SkillLevel.BEGINNER
                        )
                        
                        goal = await sync_to_async(UserLearningGoal.objects.create)(
                            user=user,
                            industry=user_industry,
                            skill_name=goal_input.skill_name,
                            description=goal_input.description,
                            target_skill_level=target_level,
                            priority=goal_input.priority
                        )
                        created_goals.append(goal)
                    
                    logger.info(f"✅ Created {len(input.goals)} learning goals")
                    
                except Exception as e:
                    logger.error(f"❌ Error creating goals: {e}")
            
            # Generate AI roadmaps
            roadmaps_data = []
            if created_goals:
                try:
                    logger.info("🤖 Generating AI-powered learning roadmaps...")
                    
                    # Prepare user profile for AI
                    learning_goals = []
                    for goal in created_goals:
                        learning_goals.append(LearningGoal(
                            skill_name=goal.skill_name,
                            description=goal.description,
                            target_skill_level=goal.target_skill_level,
                            priority=goal.priority
                        ))
                    
                    user_profile = AIUserProfile(
                        role=user.role or 'learner',
                        industry=input.industry or 'Technology',
                        career_stage=input.career_stage or 'entry_level',
                        learning_style=input.preferences.learning_style if input.preferences else 'mixed',
                        time_commitment=input.preferences.time_commitment if input.preferences else '3-5',
                        goals=learning_goals
                    )
                    
                    # Generate roadmaps using AI (sync call)
                    roadmaps = gemini_ai_service.generate_roadmaps(user_profile)
                    
                    # Convert roadmaps to GraphQL types
                    for roadmap in roadmaps:
                        steps = []
                        for step in roadmap.steps:
                            steps.append(RoadmapStep(
                                title=step.title,
                                description=step.description,
                                estimated_duration=step.estimated_duration,
                                difficulty=step.difficulty,
                                resources=step.resources,
                                skills_covered=step.skills_covered
                            ))
                        
                        roadmap_data = LearningRoadmap(
                            skill_name=roadmap.skill_name,
                            description=roadmap.description,
                            total_duration=roadmap.total_duration,
                            difficulty_level=roadmap.difficulty_level,
                            steps=steps
                        )
                        roadmaps_data.append(roadmap_data)
                    
                    logger.info(f"✅ Generated {len(roadmaps_data)} AI roadmaps")
                    
                except Exception as e:
                    logger.error(f"❌ Error generating AI roadmaps: {e}")
                    # Continue without roadmaps on error
            
            # Create response user object with profile data
            onboarding_user = OnboardingUser(
                id=str(user.id),
                email=user.email,
                first_name=profile.first_name,
                last_name=profile.last_name,
                role=user.role,
                bio=profile.bio
            )
            
            logger.info(f"✅ Onboarding completed for user: {user.email} with {len(roadmaps_data)} roadmaps")
            
            return CompleteOnboardingPayload(
                success=True,
                message="Onboarding completed successfully",
                user=onboarding_user,
                roadmaps=roadmaps_data
            )
            
        except Exception as e:
            logger.error(f"❌ Onboarding completion error: {e}")
            return CompleteOnboardingPayload(
                success=False,
                message=f"Onboarding completion failed: {str(e)}"
            )
