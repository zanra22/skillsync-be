# Onboarding Data Reference Guide

This document explains what data is collected during user onboarding and how it influences AI-powered lesson generation.

---

## Data Collection Flow

```
User Completes Onboarding
    ↓
Frontend sends CompleteOnboardingInput
    ↓
Backend creates:
    - UserProfile (personal info + learning preferences)
    - UserIndustry (primary industry)
    - UserLearningGoal (per skill, per industry)
    ↓
Data passed to AI Services
    ↓
Prompts generated with full context
    ↓
Lessons created tailored to user profile
```

---

## UserProfile Model Fields

### Personal Information
```python
first_name: str              # e.g., "Python"
last_name: str               # e.g., "Learner"
bio: str                     # Optional biography
profile_picture: ImageField  # Optional avatar
```

### Onboarding Status
```python
onboarding_completed: bool              # Is onboarding done?
onboarding_step: OnboardingStep         # Current step
# Values: welcome, role_selection, basic_info, industry_selection,
#         goals_setup, preferences, complete
```

### Professional Information
```python
skill_level: SkillLevel
# Values: BEGINNER, INTERMEDIATE, EXPERT

career_stage: CareerStage
# Values: STUDENT, ENTRY_LEVEL, MID_LEVEL, SENIOR_LEVEL,
#         EXECUTIVE, CAREER_CHANGER, FREELANCER

industry: IndustryType
# Values: TECHNOLOGY, HEALTHCARE, FINANCE, EDUCATION, MARKETING,
#         DESIGN, SALES, MANUFACTURING, CONSULTING, STARTUP,
#         NON_PROFIT, GOVERNMENT, OTHER

job_title: str                          # e.g., "Software Engineer"
company: str                            # e.g., "Google"
years_of_experience: int                # e.g., 5
```

### Learning Preferences
```python
learning_style: str
# Values: hands_on, video, reading, mixed
# How the user prefers to learn

learning_goals: str
# Free text describing learning objectives
# e.g., "Master Python basics for career development"

time_commitment: str
# Weekly hours available
# Values: 1-3, 3-5, 5-10, 10+
# Example: "3-5" means 3-5 hours per week

transition_timeline: str
# For career changers only
# Values: immediate, 6_months, 1_year, long_term
```

### Mentorship Information (Optional)
```python
mentorship_status: MentorshipStatus
# Values: AVAILABLE, BUSY, NOT_AVAILABLE, ON_BREAK
# Only if user is a mentor

mentorship_rate: Decimal              # Hourly rate in USD
mentorship_bio: str                   # Mentor expertise description
```

---

## UserIndustry Model

Tracks which industries a user is interested in:

```python
user: ForeignKey(User)              # The user
industry: IndustryType              # Industry choice
is_primary: bool                    # Mark primary industry

# Audit fields
created_at: DateTimeField
updated_at: DateTimeField
```

### Example
```python
UserIndustry.objects.create(
    user=user,
    industry=IndustryType.TECHNOLOGY,  # Primary
    is_primary=True
)
```

---

## UserLearningGoal Model

Represents a specific skill the user wants to learn:

```python
user: ForeignKey(User)                      # The user
industry: ForeignKey(UserIndustry)          # In which industry

# Goal Definition
skill_name: str                             # e.g., "Python Basics"
description: str                            # e.g., "Master the basics of Python..."
target_skill_level: SkillLevel              # BEGINNER, INTERMEDIATE, EXPERT
current_skill_level: SkillLevel             # Where they are now

# Progress Tracking
status: GoalStatus                          # NOT_STARTED, IN_PROGRESS, COMPLETED, ON_HOLD
progress_percentage: int                    # 0-100

# AI Integration
ai_roadmap_id: str                          # ID of generated roadmap
roadmap_generated_at: DateTimeField         # When roadmap was created

# Timeline
target_completion_date: DateField           # Goal deadline
started_at: DateTimeField                   # When user started
completed_at: DateTimeField                 # When completed

# Organization
priority: PositiveIntegerField              # 1=highest, 5=lowest
is_active: bool                             # Is this goal active?

# Audit
created_at: DateTimeField
updated_at: DateTimeField
```

### Example
```python
goal = UserLearningGoal.objects.create(
    user=user,
    industry=user_industry,
    skill_name='Python Basics',
    description='Master the basics of Python for Career Development',
    target_skill_level=SkillLevel.BEGINNER,
    current_skill_level=SkillLevel.BEGINNER,
    priority=1  # Highest priority
)
```

---

## How Onboarding Data Influences Lesson Generation

### 1. Learning Style Routing

Based on `UserProfile.learning_style`:

```python
learning_style = profile.learning_style

if learning_style == 'hands_on':
    # Generate coding exercises, projects, practice problems
    lesson = await generate_hands_on_lesson(...)

elif learning_style == 'video':
    # Find YouTube videos, generate study guide
    lesson = await generate_video_lesson(...)

elif learning_style == 'reading':
    # Compile docs, blog posts, articles
    lesson = await generate_reading_lesson(...)

elif learning_style == 'mixed':
    # All three combined - most comprehensive
    lesson = await generate_mixed_lesson(...)
```

### 2. Career Stage Context

Based on `UserProfile.career_stage`:

```python
career_stage = profile.career_stage

# Influences lesson depth and examples used:
if career_stage == 'student':
    # Focus on fundamentals, academic examples
    # Less professional jargon
    # More practice problems

elif career_stage == 'entry_level':
    # Focus on industry basics
    # Real-world examples
    # Career application emphasis

elif career_stage == 'senior_level':
    # Focus on advanced patterns
    # Architectural considerations
    # Scaling and optimization

elif career_stage == 'career_changer':
    # Connect to their previous experience
    # Translational examples
    # Confidence building
```

### 3. Skill Level Context

Based on `UserProfile.skill_level`:

```python
skill_level = profile.skill_level

# Influences vocabulary and depth:
if skill_level == 'beginner':
    # Explain every concept from scratch
    # Use simple analogies
    # More practice, less theory

elif skill_level == 'intermediate':
    # Build on foundations
    # Introduce advanced topics gradually
    # Balance practice and concepts

elif skill_level == 'expert':
    # Deep dive into nuances
    # Research-level content
    # Advanced optimizations
```

### 4. Time Commitment Context

Based on `UserProfile.time_commitment`:

```python
time_commitment = profile.time_commitment

# Influences lesson length:
if time_commitment == '1-3':     # 1-3 hours/week
    # Short lessons, ~30 mins each
    # Can complete 2-3 lessons/week

elif time_commitment == '3-5':   # 3-5 hours/week
    # Medium lessons, ~1-1.5 hours each
    # Can complete 3-5 lessons/week

elif time_commitment == '5-10':  # 5-10 hours/week
    # Longer lessons with projects
    # Can complete 5-7 lessons/week

elif time_commitment == '10+':   # 10+ hours/week
    # Comprehensive, project-based lessons
    # Can complete 7+ lessons/week
```

### 5. Goal Definition

Based on `UserLearningGoal`:

```python
goal = user.learning_goals.get(skill_name='Python Basics')

# Influences focus areas:
goal.skill_name              # What to teach
goal.description             # Why it matters
goal.target_skill_level      # Where to get to
goal.priority                # How important (1-5)
goal.industry                # Industry context
```

---

## Complete Prompt Generation Example

When a **Student** wants to learn **Python Basics** at **Beginner** level:

### Collected Data
```
UserProfile:
  - career_stage: "student"
  - skill_level: "beginner"
  - learning_style: "mixed"
  - time_commitment: "3-5"
  - learning_goals: "Master Python basics for career development"

UserIndustry:
  - industry: "technology"
  - is_primary: true

UserLearningGoal:
  - skill_name: "Python Basics"
  - description: "Master the basics of Python for Career Development"
  - target_skill_level: "beginner"
  - current_skill_level: "beginner"
  - priority: 1
```

### Generated Prompt (Simplified)
```
"Create a MIXED learning lesson for a STUDENT learning Python Basics at BEGINNER level:

CONTEXT:
- User is a STUDENT (focus on fundamentals)
- Current level: BEGINNER (explain from scratch)
- Target level: BEGINNER (build confidence)
- Time available: 3-5 hours/week (medium-length lessons)
- Learning style: MIXED (include hands-on, video, reading)
- Industry: Technology
- Goal: Master Python basics for career development

LESSON STRUCTURE (must include all three):

1. HANDS-ON COMPONENT:
   - Beginner-appropriate coding exercises
   - 2-3 practice problems with solutions
   - Start with simple syntax, build up

2. VIDEO COMPONENT:
   - Find 2-3 high-quality YouTube tutorials
   - Focus on concept explanation
   - Student-friendly pace

3. READING COMPONENT:
   - Compile official Python documentation sections
   - Find beginner-friendly blog posts
   - Include cheat sheets and quick references

TONE: Encouraging, simple, practice-focused
DURATION: 60-90 minutes total
ASSESSMENT: Include 3-5 quick self-check questions"
```

### Result
This produces a lesson that is:
- ✅ Appropriate for students (not too technical)
- ✅ Suitable for beginners (thorough explanations)
- ✅ Fits time commitment (not overwhelming)
- ✅ Matches learning preference (multiple formats)
- ✅ Relevant to industry (technology examples)
- ✅ Goal-aligned (mastering Python basics)

---

## Database Relationships Diagram

```
User (Django Auth)
  ↓
  ├─→ UserProfile (1:1)
  │     Contains: name, learning preferences, career info
  │
  ├─→ UserIndustry (1:M)
  │     Contains: industry choices (primary + secondary)
  │
  └─→ UserLearningGoal (1:M)
        Contains: specific skills per industry
        ↓
        Used for AI roadmap generation
```

---

## Frontend GraphQL Input Example

```graphql
mutation CompleteOnboarding($input: CompleteOnboardingInput!) {
  completeOnboarding(input: $input) {
    success
    user {
      id
      email
      role
    }
  }
}

# Input example:
{
  "input": {
    "role": "learner",
    "first_name": "Python",
    "last_name": "Learner",
    "bio": "Interested in learning Python",
    "career_stage": "student",
    "industry": "Technology",
    "goals": [
      {
        "skill_name": "Python Basics",
        "description": "Master the basics of Python for Career Development",
        "target_skill_level": "beginner",
        "priority": 1
      }
    ],
    "preferences": {
      "learning_style": "mixed",
      "time_commitment": "3-5"
    }
  }
}
```

---

## Testing with Realistic Onboarding Data

To test AI generation with realistic student data:

```bash
# Run the comprehensive test
pytest tests/test_ai_with_realistic_onboarding.py -v -s

# This creates a student profile with:
# - Career Stage: STUDENT
# - Skill Level: BEGINNER
# - Learning Style: MIXED
# - Goal: Master the basics of Python for Career Development
# - Industry: TECHNOLOGY

# And generates lessons for all three learning styles
```

---

## Key Takeaways

1. **UserProfile** - Overall user context (career stage, learning style, time available)
2. **UserIndustry** - Industry specialization context
3. **UserLearningGoal** - Specific skill definition per industry
4. **Combined** - All data flows into AI prompt generation for personalized lessons

This ensures every generated lesson is tailored to:
- Who the user is (career stage)
- What they know (skill level)
- How they like to learn (learning style)
- How much time they have (time commitment)
- What they want to learn (goal definition)
- What field they're in (industry)

---

## For Backend Developers

When implementing new features that use onboarding data:

```python
# Get user's complete onboarding context
user = request.user
profile = user.profile
goal = user.learning_goals.get(skill_name='Python Basics')
industry = goal.industry

# Use in your logic
if profile.learning_style == 'hands_on':
    # ... hands-on specific code

# When generating content
lesson_context = {
    'career_stage': profile.career_stage,
    'skill_level': profile.skill_level,
    'learning_style': profile.learning_style,
    'industry': industry.industry,
    'time_commitment': profile.time_commitment,
}

# Always pass context to AI services
lesson = await lesson_service.generate_lesson(
    user_profile=lesson_context,
    goal=goal
)
```

---

## For Frontend Developers

When building the onboarding flow, collect:

1. **Step 1: Role Selection** → Sets `user.role`
2. **Step 2: Basic Info** → Sets name, bio
3. **Step 3: Industry Selection** → Creates `UserIndustry`
4. **Step 4: Career Stage** → Sets `profile.career_stage`
5. **Step 5: Learning Goals** → Creates `UserLearningGoal` entries
6. **Step 6: Preferences** → Sets learning_style, time_commitment

All this data feeds into AI generation for personalized learning experiences!
