from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
import json
import logging
from profiles.models import UserIndustry, UserLearningGoal
from helpers.ai_roadmap_service import gemini_ai_service, UserProfile, LearningGoal

logger = logging.getLogger(__name__)
User = get_user_model()

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def complete_onboarding(request):
    """
    Complete user onboarding by updating profile and creating goals.
    """
    try:
        logger.info(f"🚀 Processing onboarding completion for user: {request.user.email}")
        
        # Parse request data
        data = json.loads(request.body)
        logger.info(f"📦 Onboarding data received: {data}")
        
        # Update user profile
        user = request.user
        user.role = data.get('role')
        user.first_name = data.get('firstName', '')
        user.last_name = data.get('lastName', '')
        
        # Update bio if provided
        if hasattr(user, 'bio') and data.get('bio'):
            user.bio = data.get('bio')
        
        user.save()
        logger.info(f"✅ User profile updated: {user.email}")
        
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
                
                user_industry, created = UserIndustry.objects.get_or_create(
                    user=user,
                    industry=industry_choice,
                    defaults={'is_primary': True}
                )
                if not created:
                    user_industry.is_primary = True
                    user_industry.save()
                
                logger.info(f"✅ Industry updated: {industry_name} - {career_stage}")
            except Exception as e:
                logger.error(f"❌ Error updating industry: {e}")
                # Create a default technology industry if there's an error
                user_industry, _ = UserIndustry.objects.get_or_create(
                    user=user,
                    industry=IndustryType.TECHNOLOGY,
                    defaults={'is_primary': True}
                )
        
        # Handle learning goals
        goals_data = data.get('goals', [])
        created_goals = []
        
        if goals_data and user_industry:
            try:
                # Clear existing goals for this industry
                UserLearningGoal.objects.filter(user=user, industry=user_industry).delete()
                
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
                    
                    goal = UserLearningGoal.objects.create(
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
            # For now, we'll log them. In production, you might want to store these
            # in a separate UserPreferences model or in the user profile
        
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
                
                user_profile = UserProfile(
                    role=user.role or 'learner',
                    industry=industry_name or 'Technology',
                    career_stage=career_stage or 'entry_level',
                    learning_style=preferences.get('learningStyle', 'mixed'),
                    time_commitment=preferences.get('timeCommitment', '3-5'),
                    goals=learning_goals
                )
                
                # Generate roadmaps using AI
                roadmaps = gemini_ai_service.generate_roadmaps(user_profile)
                
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
        response_data = {
            'success': True,
            'message': 'Onboarding completed successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'bio': getattr(user, 'bio', ''),
            },
            'roadmaps': roadmaps_data
        }
        
        logger.info(f"✅ Onboarding completed for user: {user.email} with {len(roadmaps_data)} roadmaps")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in request body")
        return JsonResponse(
            {'error': 'Invalid JSON in request body'},
            status=400
        )
    except Exception as e:
        logger.error(f"❌ Onboarding completion error: {e}")
        return JsonResponse(
            {'error': 'Internal server error', 'details': str(e)},
            status=500
        )
