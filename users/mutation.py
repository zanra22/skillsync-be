import strawberry
import strawberry_django
import json
import logging
from typing import List, Optional
from .types import UserType, OnboardingResponse
from onboarding.types import LearningGoalInput as OnboardingLearningGoalInput
from asgiref.sync import sync_to_async

from django.contrib.auth import get_user_model
from profiles.models import UserIndustry, UserLearningGoal
from helpers.ai_roadmap_service import UserProfile as AIUserProfile, LearningGoal

User = get_user_model()
logger = logging.getLogger(__name__)

def normalize_time_commitment(frontend_value: str) -> str:
    """
    Convert frontend time commitment values to backend format.

    Frontend sends: 'casual', 'steady', 'focused', 'intensive'
    Backend expects: '1-3', '3-5', '5-10', '10+'
    """
    mapping = {
        'casual': '1-3',
        'steady': '3-5',
        'focused': '5-10',
        'intensive': '10+'
    }
    return mapping.get(frontend_value, frontend_value)  # Return as-is if already in backend format


def generate_bio_from_onboarding(data: dict) -> str:
    """
    Generate a meaningful bio from onboarding data based on role and goals.
    """
    role = data.get('role', '')
    current_role = data.get('currentRole', '')
    industry = data.get('industry', '')
    goals = data.get('goals', [])
    transition_timeline = data.get('transitionTimeline', '')

    # Extract skill names from goals
    skill_names = [goal.get('skillName', '') for goal in goals[:2]]  # First 2 skills
    skills_text = ', '.join(skill_names) if skill_names else 'new technologies'

    if role == 'career_changer':
        timeline_text = ''
        if transition_timeline == 'immediate':
            timeline_text = 'actively seeking opportunities'
        elif transition_timeline == '6_months':
            timeline_text = 'planning to transition within 6-12 months'
        elif transition_timeline == '1_year':
            timeline_text = 'working towards transition over 1-2 years'
        else:
            timeline_text = 'developing skills for future transition'

        return f"{current_role} transitioning to {industry}, {timeline_text}. Focused on learning {skills_text}."

    elif role == 'professional':
        return f"{current_role} looking to advance skills in {industry}. Currently developing expertise in {skills_text}."

    elif role == 'student':
        return f"Student passionate about {industry}. Learning {skills_text} to build a strong foundation for my career."

    else:
        return f"Learner interested in {industry}, focused on developing skills in {skills_text}."


@strawberry.type
class UsersMutation:  # Renamed from Mutation to UsersMutation
    @strawberry.mutation
    async def create_user(self, username: str, email: str, password: str) -> UserType:
        user = await sync_to_async(User.objects.create_user)(
            username=username,
            email=email,
            password=password
        )
        return user

    @strawberry.mutation
    async def complete_onboarding(self, info, role: str, firstName: str, lastName: str, currentRole: str, industry: str, careerStage: str, transitionTimeline: Optional[str] = None, goals: Optional[List[OnboardingLearningGoalInput]] = None, learningStyle: Optional[str] = None, timeCommitment: Optional[str] = None) -> OnboardingResponse:
        """
        Complete user onboarding by updating profile and creating goals.
        """
        try:
            # Get user from GraphQL context
            user = info.context.request.user
            if not user.is_authenticated:
                return OnboardingResponse(
                    success=False,
                    message="User not authenticated",
                    user=None,
                    roadmaps="[]"
                )

            logger.info(f"🚀 Processing onboarding completion for user: {user.email}")

            # Convert input to dict for processing. Support both attribute-style
            # Strawberry input objects and plain dicts for robustness.
            def _extract_goal(g):
                if g is None:
                    return {}
                # handle dicts
                if isinstance(g, dict):
                    return {
                        'skillName': g.get('skillName') or g.get('skill_name'),
                        'description': g.get('description'),
                        'targetSkillLevel': g.get('targetSkillLevel') or g.get('target_skill_level'),
                        'priority': g.get('priority', 1),
                    }
                # handle attribute-style objects from Strawberry
                return {
                    'skillName': getattr(g, 'skillName', None) or getattr(g, 'skill_name', None),
                    'description': getattr(g, 'description', None),
                    'targetSkillLevel': getattr(g, 'targetSkillLevel', None) or getattr(g, 'target_skill_level', None),
                    'priority': getattr(g, 'priority', 1),
                }

            data = {
                'role': role,
                'firstName': firstName,
                'lastName': lastName,
                'currentRole': currentRole,
                'industry': industry,
                'careerStage': careerStage,
                'transitionTimeline': transitionTimeline,
                'goals': [_extract_goal(g) for g in goals] if goals else [],
                'preferences': {'learningStyle': learningStyle, 'timeCommitment': timeCommitment} if (learningStyle or timeCommitment) else {}
            }

            logger.info(f"📦 Onboarding data received: {data}")

            # Update user profile (user is retrieved from info.context above)
            user.role = data.get('role')
            user.first_name = data.get('firstName', '')
            user.last_name = data.get('lastName', '')

            await sync_to_async(user.save)()
            logger.info(f"✅ User profile updated: {user.email}")

            # Create or update UserProfile with all onboarding data
            from profiles.models import UserProfile
            profile, created = await sync_to_async(UserProfile.objects.get_or_create)(user=user)

            # Store basic profile information
            profile.first_name = data.get('firstName', '')
            profile.last_name = data.get('lastName', '')

            # Store currentRole in job_title field according to role logic
            current_role = data.get('currentRole', '')
            if current_role:
                profile.job_title = current_role
            elif user.role == 'student':
                profile.job_title = 'student'  # For students, both role and currentRole are 'student'

            logger.info(f"✅ UserProfile {'created' if created else 'updated'} with job_title: {profile.job_title}")

            # Handle industry selection
            industry_name = data.get('industry')
            career_stage = data.get('careerStage')
            user_industry = None

            if industry_name:
                try:
                    # Map the industry name to the choice value
                    from profiles.choices import IndustryType
                    industry_mapping = {
                        'Technology': IndustryType.TECHNOLOGY,
                        'Software Development': IndustryType.TECHNOLOGY,
                        'Healthcare': IndustryType.HEALTHCARE,
                        'Finance': IndustryType.FINANCE,
                        'Education': IndustryType.EDUCATION,
                        'Manufacturing': IndustryType.MANUFACTURING,
                        'Retail': IndustryType.RETAIL,
                        'Consulting': IndustryType.CONSULTING,
                        'Media': IndustryType.MEDIA,
                        'Non-profit': IndustryType.NON_PROFIT,
                        'Government': IndustryType.GOVERNMENT,
                        'Other': IndustryType.OTHER,
                    }

                    industry_choice = industry_mapping.get(industry_name, IndustryType.OTHER)

                    user_industry, created = await sync_to_async(UserIndustry.objects.get_or_create)(
                        user=user,
                        industry=industry_choice,
                        defaults={'is_primary': True}
                    )
                    if not created:
                        user_industry.is_primary = True
                        await sync_to_async(user_industry.save)()

                    logger.info(f"✅ Industry updated: {industry_name} - {career_stage}")
                except Exception as e:
                    logger.error(f"❌ Error updating industry: {e}")
                    # Create a default technology industry if there's an error
                    user_industry, _ = await sync_to_async(UserIndustry.objects.get_or_create)(
                        user=user,
                        industry=IndustryType.TECHNOLOGY,
                        defaults={'is_primary': True}
                    )

            # Store career stage and transition timeline in profile
            if career_stage:
                profile.career_stage = career_stage

            # Handle transition timeline for career changers
            transition_timeline = data.get('transitionTimeline', '')
            if transition_timeline and user.role == 'career_changer':
                profile.transition_timeline = transition_timeline
                logger.info(f"✅ Career changer transition timeline set: {transition_timeline}")

            # Store preferences in profile
            preferences = data.get('preferences', {})
            if preferences:
                if preferences.get('learningStyle'):
                    profile.learning_style = preferences.get('learningStyle')
                if preferences.get('timeCommitment'):
                    profile.time_commitment = normalize_time_commitment(preferences.get('timeCommitment', 'steady'))

            # Generate smart bio from onboarding data if no bio provided
            if not profile.bio:
                profile.bio = generate_bio_from_onboarding(data)

            await sync_to_async(profile.save)()
            logger.info(f"✅ Profile saved with career_stage: {profile.career_stage}, transition_timeline: {profile.transition_timeline}")

            # Handle learning goals
            goals_data = data.get('goals', [])
            created_goals = []

            if goals_data and user_industry:
                try:
                    # Clear existing goals for this industry
                    await sync_to_async(UserLearningGoal.objects.filter(user=user, industry=user_industry).delete)()

                    # Create new goals
                    for goal_data in goals_data:
                        # Map target skill level to choice value
                        from profiles.choices import SkillLevel
                        skill_level_mapping = {
                            'beginner': SkillLevel.BEGINNER,
                            'intermediate': SkillLevel.INTERMEDIATE,
                            'advanced': SkillLevel.INTERMEDIATE,  # Map advanced to intermediate for now
                            'expert': SkillLevel.EXPERT,
                        }

                        target_level = skill_level_mapping.get(
                            goal_data.get('targetSkillLevel', 'beginner'),
                            SkillLevel.BEGINNER
                        )

                        goal = await sync_to_async(UserLearningGoal.objects.create)(
                            user=user,
                            industry=user_industry,
                            skill_name=goal_data.get('skillName', ''),
                            description=goal_data.get('description', ''),
                            target_skill_level=target_level,
                            priority=goal_data.get('priority', 1)
                        )
                        created_goals.append(goal)

                    logger.info(f"✅ Created {len(goals_data)} learning goals")
                except Exception as e:
                    logger.error(f"❌ Error creating goals: {e}")
            elif goals_data and not user_industry:
                logger.warning("⚠️ Cannot create goals without industry - skipping goal creation")

            # Handle preferences (store in user profile or separate model if needed)
            preferences = data.get('preferences', {})
            if preferences:
                logger.info(f"📝 Preferences received: {preferences}")

            # Generate AI roadmaps
            roadmaps_data = []
            if created_goals:
                try:
                    logger.info("🤖 Generating AI-powered learning roadmaps...")

                    # Prepare user profile for AI
                    learning_goals = [
                        LearningGoal(
                            skill_name=goal.skill_name,
                            description=goal.description,
                            target_skill_level=goal.target_skill_level,
                            priority=goal.priority
                        )
                        for goal in created_goals
                    ]

                    user_profile = AIUserProfile(
                        role=user.role or 'learner',
                        industry=industry_name or 'Technology',
                        career_stage=career_stage or 'entry_level',
                        learning_style=preferences.get('learningStyle', 'mixed'),
                        time_commitment=normalize_time_commitment(preferences.get('timeCommitment', 'steady')),
                        goals=learning_goals
                    )

                    # Generate roadmaps using AI (run in thread pool to avoid blocking)
                    from concurrent.futures import ThreadPoolExecutor
                    import asyncio


                    from helpers.ai_roadmap_service import HybridRoadmapService
                    def generate_roadmaps_sync():
                        return HybridRoadmapService().generate_roadmaps(user_profile)

                    loop = asyncio.get_event_loop()
                    roadmaps = await loop.run_in_executor(None, generate_roadmaps_sync)

                    # Convert roadmaps to JSON serializable format
                    for roadmap in roadmaps:
                        roadmap_data = {
                            'skill_name': roadmap.skill_name,
                            'description': roadmap.description,
                            'total_duration': roadmap.total_duration,
                            'difficulty_level': roadmap.difficulty_level,
                            'steps': [
                                {
                                    'title': step.title,
                                    'description': step.description,
                                    'estimated_duration': step.estimated_duration,
                                    'difficulty': step.difficulty,
                                    'resources': step.resources,
                                    'skills_covered': step.skills_covered
                                }
                                for step in roadmap.steps
                            ]
                        }
                        roadmaps_data.append(roadmap_data)

                    logger.info(f"✅ Generated {len(roadmaps_data)} AI roadmaps")

                except Exception as e:
                    logger.error(f"❌ Error generating AI roadmaps: {e}")
                    # Continue without roadmaps on error

            # Return success response with updated user data and roadmaps
            logger.info(f"✅ Onboarding completed for user: {user.email} with {len(roadmaps_data)} roadmaps")

            return OnboardingResponse(
                success=True,
                message="Onboarding completed successfully",
                user=user,
                roadmaps=json.dumps(roadmaps_data)  # Convert to JSON string for GraphQL
            )

        except Exception as e:
            logger.error(f"❌ Onboarding completion error: {e}")
            # Get user from context for error response
            user = info.context.request.user if hasattr(info.context, 'request') else None
            return OnboardingResponse(
                success=False,
                message=f"Internal server error: {str(e)}",
                user=user,
                roadmaps="[]"
            )