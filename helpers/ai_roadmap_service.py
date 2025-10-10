import logging
from typing import List, Dict, Any, Optional
import json
import os
import requests
from dataclasses import dataclass

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
    role: str
    industry: str
    career_stage: str
    learning_style: str
    time_commitment: str
    goals: List[LearningGoal]

@dataclass
class RoadmapStep:
    title: str
    description: str
    estimated_duration: str
    difficulty: str
    resources: List[str]
    skills_covered: List[str]

@dataclass
class LearningRoadmap:
    skill_name: str
    description: str
    total_duration: str
    difficulty_level: str
    steps: List[RoadmapStep]

class GeminiAIService:
    """
    Service for generating personalized learning roadmaps using Google's Gemini AI.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        # Use gemini-2.0-flash-exp (same as lesson service - working model)
        self.api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent'
        
        if not self.api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found in environment variables")
    
    def generate_roadmaps(self, user_profile: UserProfile) -> List[LearningRoadmap]:
        """
        Generate personalized learning roadmaps for all user goals.
        """
        if not self.api_key:
            logger.error("❌ Cannot generate roadmaps: GEMINI_API_KEY not configured")
            return self._get_fallback_roadmaps(user_profile)
        
        roadmaps = []
        
        for goal in user_profile.goals:
            try:
                roadmap = self._generate_single_roadmap(user_profile, goal)
                if roadmap:
                    roadmaps.append(roadmap)
            except Exception as e:
                logger.error(f"❌ Failed to generate roadmap for {goal.skill_name}: {e}")
                # Add fallback roadmap for this goal
                fallback = self._get_fallback_roadmap(goal)
                if fallback:
                    roadmaps.append(fallback)
        
        return roadmaps
    
    def _generate_single_roadmap(self, user_profile: UserProfile, goal: LearningGoal) -> Optional[LearningRoadmap]:
        """
        Generate a single roadmap for a specific learning goal.
        """
        logger.info(f"🤖 Generating roadmap for: {goal.skill_name}")
        
        prompt = self._create_roadmap_prompt(user_profile, goal)
        
        try:
            # Call Gemini API
            headers = {
                'Content-Type': 'application/json',
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,  # Lower for more consistent, focused responses
                    "topK": 20,          # Reduced for more focused vocabulary
                    "topP": 0.8,         # Slightly reduced for more predictable output
                    "maxOutputTokens": 4096,  # Increased for detailed responses
                    "candidateCount": 1,
                    "stopSequences": ["```\n\n"]  # Stop after JSON block
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH", 
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # 🚀 LOG THE RAW GEMINI RESPONSE FOR MONGODB PREPARATION
                logger.info(f"🤖 RAW GEMINI RESPONSE for {goal.skill_name}:")
                logger.info("=" * 80)
                logger.info(generated_text)
                logger.info("=" * 80)
                
                # Parse the AI response into structured roadmap
                roadmap = self._parse_ai_response(generated_text, goal)
                
                if roadmap:
                    # 🚀 LOG THE PARSED STRUCTURED DATA FOR MONGODB SCHEMA DESIGN
                    logger.info(f"📊 STRUCTURED ROADMAP DATA for {goal.skill_name}:")
                    logger.info("=" * 60)
                    roadmap_dict = {
                        "skill_name": roadmap.skill_name,
                        "description": roadmap.description,
                        "total_duration": roadmap.total_duration,
                        "difficulty_level": roadmap.difficulty_level,
                        "steps": [
                            {
                                "title": step.title,
                                "description": step.description,
                                "estimated_duration": step.estimated_duration,
                                "difficulty": step.difficulty,
                                "resources": step.resources,
                                "skills_covered": step.skills_covered
                            } for step in roadmap.steps
                        ]
                    }
                    logger.info(json.dumps(roadmap_dict, indent=2, ensure_ascii=False))
                    logger.info("=" * 60)
                    
                    logger.info(f"✅ Generated roadmap for {goal.skill_name}")
                    return roadmap
                else:
                    logger.error(f"❌ Failed to parse roadmap for {goal.skill_name}")
                    return None
            else:
                logger.error(f"❌ Gemini API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error calling Gemini API: {e}")
            return None
    
    def _create_roadmap_prompt(self, user_profile: UserProfile, goal: LearningGoal) -> str:
        """
        Create a detailed prompt for AI roadmap generation.
        """
        
        # Define learning style specific resource guidance
        style_guidance = {
            'hands_on': 'Prioritize practical projects, coding exercises, labs, and interactive tutorials. Include 70% hands-on resources with specific project suggestions.',
            'video': 'Focus on video tutorials, recorded lectures, and visual demonstrations. Include 70% video-based resources with specific course recommendations.',
            'reading': 'Emphasize written documentation, articles, books, and text-based guides. Include 70% reading materials with specific book/article titles.',
            'interactive': 'Prioritize interactive courses, discussions, mentoring, and collaborative learning. Include 70% interactive resources with community engagement.',
            'mixed': 'Provide a balanced mix of videos (30%), hands-on projects (30%), reading materials (25%), and interactive content (15%).'
        }
        
        style_instruction = style_guidance.get(user_profile.learning_style, style_guidance['mixed'])
        
        # Create industry-specific context
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
        
        # Time commitment guidance
        time_mapping = {
            '1-2': 'micro-learning sessions (15-30 min daily)',
            '3-5': 'focused study sessions (45-90 min, 3-4 times/week)',
            '5-10': 'intensive learning blocks (2-3 hours, 4-5 times/week)',
            '10+': 'immersive learning (3+ hours daily)'
        }
        
        time_guidance = time_mapping.get(user_profile.time_commitment, 'moderate study sessions')
        
        return f"""You are an expert learning consultant and curriculum designer with 15+ years of experience in {user_profile.industry} industry training. Create a highly detailed, personalized learning roadmap that will transform this learner from their current level to their target proficiency.

**LEARNER PROFILE:**
🎯 Role: {user_profile.role} ({user_profile.career_stage} level)
🏢 Industry: {user_profile.industry}
📚 Learning Style: {user_profile.learning_style}
⏰ Weekly Commitment: {user_profile.time_commitment} hours ({time_guidance})

**SPECIFIC LEARNING GOAL:**
🎯 Skill: {goal.skill_name}
📝 Objective: {goal.description}
🎚️ Target Mastery: {goal.target_skill_level} level
⭐ Priority: {goal.priority}/5 (higher = more urgent)

**INDUSTRY CONTEXT:** {industry_note}

**LEARNING STYLE OPTIMIZATION:** {style_instruction}

**CRITICAL REQUIREMENTS:**
1. **Specificity**: Provide exact resource names, tools, platforms, and websites
2. **Measurable Outcomes**: Include specific skills/knowledge gained per step
3. **Industry Relevance**: All content must align with {user_profile.industry} industry needs
4. **Time Optimization**: Structure for {time_guidance}
5. **Progressive Difficulty**: Each step builds logically on the previous one
6. **Real-world Application**: Include practical projects and portfolio pieces

**RESOURCE QUALITY STANDARDS:**
- Only recommend resources that actually exist and are currently available
- Prioritize well-rated, recent content (2020+)
- Include mix of free and premium options
- Specify exact course/book/tool names, not generic descriptions

**OUTPUT FORMAT (STRICT JSON):**
```json
{{
  "skill_name": "{goal.skill_name}",
  "description": "Compelling 2-sentence overview of the complete learning journey and career impact",
  "total_duration": "realistic timeframe based on {user_profile.time_commitment} hours/week",
  "difficulty_level": "{goal.target_skill_level}",
  "steps": [
    {{
      "title": "Engaging step name that clearly states the milestone",
      "description": "Detailed 3-4 sentence description of what learner will master, why it matters, and how it connects to their {user_profile.role} role",
      "estimated_duration": "specific timeframe (e.g., '2 weeks at 5 hours/week')",
      "difficulty": "beginner|intermediate|advanced",
      "resources": [
        "Exact resource name with author/platform (e.g., 'JavaScript: The Good Parts by Douglas Crockford')",
        "Specific course title (e.g., 'React Complete Guide 2024 by Maximilian Schwarzmüller on Udemy')",
        "Precise tool/website (e.g., 'CodePen.io for practice exercises')"
      ],
      "skills_covered": [
        "Specific, measurable skill #1",
        "Specific, measurable skill #2",
        "Specific, measurable skill #3"
      ]
    }}
  ]
}}
```

**VALIDATION CHECKLIST:**
✅ Each step has 3-5 specific, real resources
✅ Skills covered are measurable and industry-relevant
✅ Total duration matches weekly commitment
✅ Resources match the {user_profile.learning_style} learning preference
✅ Content progresses logically from {goal.target_skill_level} foundations to mastery
✅ Industry context ({user_profile.industry}) is woven throughout

Create 4-6 progressive steps that will genuinely prepare this {user_profile.role} to excel with {goal.skill_name} in the {user_profile.industry} industry."""
    
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
                # Remove any trailing commas before closing brackets/braces
                json_data = re.sub(r',(\s*[}\]])', r'\1', json_data)
                
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
                for i, step_data in enumerate(roadmap_data.get('steps', [])):
                    # Validate step data
                    step_title = step_data.get('title', f'Step {i+1}')
                    step_description = step_data.get('description', 'Learning step description')
                    step_duration = step_data.get('estimated_duration', '1-2 weeks')
                    step_difficulty = step_data.get('difficulty', 'intermediate')
                    step_resources = step_data.get('resources', [])
                    step_skills = step_data.get('skills_covered', [])
                    
                    # Ensure resources and skills are lists
                    if not isinstance(step_resources, list):
                        step_resources = [str(step_resources)] if step_resources else []
                    if not isinstance(step_skills, list):
                        step_skills = [str(step_skills)] if step_skills else []
                    
                    step = RoadmapStep(
                        title=step_title,
                        description=step_description,
                        estimated_duration=step_duration,
                        difficulty=step_difficulty,
                        resources=step_resources,
                        skills_covered=step_skills
                    )
                    steps.append(step)
                
                roadmap = LearningRoadmap(
                    skill_name=roadmap_data.get('skill_name', goal.skill_name),
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
            logger.debug(f"Attempted to parse: {json_data[:500] if json_data else 'No JSON data'}...")
            return None
        except Exception as e:
            logger.error(f"❌ Error parsing AI response: {e}")
            logger.debug(f"AI Response: {ai_text[:500]}...")
            return None
    
    def _get_fallback_roadmaps(self, user_profile: UserProfile) -> List[LearningRoadmap]:
        """
        Return fallback roadmaps when AI is unavailable.
        """
        logger.info("🔄 Using fallback roadmaps")
        roadmaps = []
        
        for goal in user_profile.goals:
            fallback = self._get_fallback_roadmap(goal)
            if fallback:
                roadmaps.append(fallback)
        
        return roadmaps
    
    def _get_fallback_roadmap(self, goal: LearningGoal) -> LearningRoadmap:
        """
        Generate a basic fallback roadmap for a goal.
        """
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

# Create global instance
gemini_ai_service = GeminiAIService()