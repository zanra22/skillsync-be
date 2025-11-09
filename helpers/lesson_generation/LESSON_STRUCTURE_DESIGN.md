# Lesson Structure & Scheduling Design

## Overview

Lessons are **structured** based on cognitive science and user context, then **scheduled** based on time availability.

**Key Principle:** Optimal lesson duration is non-negotiable (15-30 min). Time commitment determines pacing, not duration.

---

## Part 1: Lesson Structure (Content Generation)

### Input Factors (Determine Structure)

1. **Topic Complexity** (`simple` | `medium` | `complex`)
   - Simple: Basic syntax, single concepts (loops, variables)
   - Medium: Multi-step procedures (functions, error handling)
   - Complex: Advanced patterns, systems thinking (async/await, design patterns)

2. **Learning Style** (`hands_on` | `video` | `reading` | `mixed`)
   - Each has research-backed optimal duration

3. **User Context**
   - **Current Skill Level** (`beginner` | `intermediate` | `expert`)
   - **User Role** (`student` | `professional` | `career_shifter`)

### Output: Lesson Metadata

```python
{
    'num_parts': int,                          # How many parts to split into
    'optimal_duration_per_part': int,          # Minutes (15-30, research-backed)
    'content_depth': str,                      # 'foundational' | 'comprehensive' | 'advanced'
    'ai_instructions': str,                    # Tell AI the part context
    'expected_completion_time': int            # Total time if user does all parts
}
```

### Decision Matrix

**How many parts based on complexity + skill level:**

| Complexity | Beginner | Intermediate | Expert |
|------------|----------|--------------|--------|
| Simple    | 1        | 1            | 1      |
| Medium    | 3        | 2            | 1      |
| Complex   | 5        | 3            | 2      |

**Adjustments by user role:**
- **Career Shifter:** +1 part (more context-building needed)
- **Professional:** Same parts, higher content depth
- **Student:** Default behavior

**Content depth determination:**

| Skill Level  | Content Depth     | Includes                              |
|-------------|------------------|---------------------------------------|
| Beginner    | Foundational      | Core concepts, simple examples        |
| Intermediate| Comprehensive     | Core + practical use + common pitfalls|
| Expert      | Advanced          | Edge cases, optimization, patterns    |

### Optimal Duration by Learning Style (Research-Backed)

| Learning Style | Optimal Duration | Basis                    |
|----------------|------------------|--------------------------|
| Video          | 15 minutes       | Attention span limit     |
| Reading        | 25 minutes       | Cognitive load (reading) |
| Hands-on       | 30 minutes       | Cognitive load (coding)  |
| Mixed          | 20 minutes       | Balanced                 |

---

## Part 2: Lesson Scheduling (Pacing)

### Input: Time Commitment

User's weekly availability:
- `1-3 hours/week` → ~1 session/week
- `3-5 hours/week` → ~2 sessions/week
- `5-10 hours/week` → ~3 sessions/week
- `10+ hours/week` → ~4 sessions/week

### Output: Schedule Metadata

```python
{
    'sessions_per_week': int,
    'weeks_to_complete_all_parts': float,
    'recommended_schedule': [
        {
            'part_number': 1,
            'suggested_week': 1,
            'spaced_reviews': ['Day 2', 'Day 7', 'Day 30']
        },
        {
            'part_number': 2,
            'suggested_week': 2,
            'spaced_reviews': ['Day 2', 'Day 7', 'Day 30']
        }
    ],
    'ui_message': str  # "At your pace, complete this topic in 3 weeks"
}
```

### Spaced Learning Schedule

Based on research (Ebbinghaus forgetting curve):
- **Day 1:** Initial learning
- **Day 2:** First review (prevents 70% forgetting)
- **Day 7:** Reinforce long-term memory
- **Day 30:** Lock into long-term retention

---

## Example Scenarios

### Scenario 1: Beginner with Limited Time
```
Topic: Python Data Types (MEDIUM complexity)
User: Student, Beginner, 1-3 hours/week, Hands-on learning

Structure (from decision matrix):
├─ num_parts: 3 (medium + beginner)
├─ duration_per_part: 30 minutes
├─ content_depth: foundational
├─ total_time: 90 minutes
└─ AI prompt: "Generate Part 1/3. Focus on core concepts only. Student is beginner..."

Schedule (from time_commitment):
├─ sessions_per_week: 1
├─ weeks_to_complete: 3 weeks
├─ Week 1: Part 1 (review Day 2, 7, 30)
├─ Week 2: Part 2 (review Day 2, 7, 30)
└─ Week 3: Part 3 (review Day 2, 7, 30)

UI Message: "Complete this topic in 3 weeks at 1 session per week"
```

### Scenario 2: Expert with Full Availability
```
Topic: Async/Await (COMPLEX complexity)
User: Professional, Expert, 10+ hours/week, Hands-on learning

Structure (from decision matrix):
├─ num_parts: 2 (complex + expert, no career shifter adjustment)
├─ duration_per_part: 30 minutes
├─ content_depth: advanced
├─ total_time: 60 minutes
└─ AI prompt: "Generate Part 1/2. Advanced patterns, edge cases. Expert level..."

Schedule (from time_commitment):
├─ sessions_per_week: 4
├─ weeks_to_complete: 0.5 weeks (can do both in 1 week)
├─ Part 1: Early week (review spaced as schedule allows)
└─ Part 2: Mid-week (review spaced as schedule allows)

UI Message: "Complete this topic in 1 week with intensive study"
```

### Scenario 3: Career Shifter with Moderate Time
```
Topic: Functions in Python (MEDIUM complexity)
User: Career Shifter, Intermediate, 3-5 hours/week, Reading learning

Structure (from decision matrix):
├─ num_parts: 3 (medium + intermediate = 2, +1 for career shifter)
├─ duration_per_part: 25 minutes
├─ content_depth: comprehensive
├─ total_time: 75 minutes
└─ AI prompt: "Generate Part 1/3. Comprehensive coverage with context for career transition. Intermediate level..."

Schedule (from time_commitment):
├─ sessions_per_week: 2
├─ weeks_to_complete: 1.5 weeks
├─ Week 1: Part 1, Part 2 (spaced across week)
├─ Week 2: Part 3
└─ Review: Distributed across 30-day window

UI Message: "Complete this topic in 1.5 weeks at 2 sessions per week"
```

---

## Implementation Checklist

### In Lesson Generation (ai_lesson_service.py or ai_roadmap_service.py)

- [ ] Before generating lesson, call `calculate_lesson_structure()`:
  ```python
  structure = calculate_lesson_structure(
      topic_complexity='medium',
      learning_style='hands_on',
      user_role='student',
      current_skill_level='beginner'
  )
  ```

- [ ] Generate `structure['num_parts']` lesson parts with:
  ```python
  for part in range(1, structure['num_parts'] + 1):
      ai_prompt = f"""
      Generate Part {part}/{structure['num_parts']}.
      Content depth: {structure['content_depth']}
      Duration: {structure['optimal_duration_per_part']} minutes
      [rest of prompt...]
      """
  ```

- [ ] After generating parts, call `calculate_schedule()`:
  ```python
  schedule = calculate_schedule(
      num_parts=structure['num_parts'],
      sessions_per_week=sessions_per_week,
      spaced_learning=True
  )
  ```

- [ ] Store in LessonContent model:
  ```python
  lesson.lesson_metadata = {
      'num_parts': structure['num_parts'],
      'part_number': part_num,
      'total_parts': structure['num_parts'],
      'content_depth': structure['content_depth'],
      'optimal_duration': structure['optimal_duration_per_part'],
      'schedule': schedule,
      'weeks_to_complete_all': schedule['weeks_to_complete_all_parts']
  }
  ```

### In Database Schema

Add fields to LessonContent model:
```python
lesson_metadata = JSONField(default=dict)  # Stores all above metadata
part_number = IntegerField(null=True)      # Which part is this? (1, 2, 3, etc)
total_parts = IntegerField(null=True)      # Total parts for this lesson (3, 5, etc)
content_depth = CharField(choices=[...])   # 'foundational', 'comprehensive', 'advanced'
optimal_duration_minutes = IntegerField()  # 15, 20, 25, or 30
```

### In Frontend/Mobile

Display metadata to user:
- "Part 1 of 3 | 30 minutes | Foundational"
- "📅 Suggested: Week 1 of 3 | Next: Review on Day 2"
- "✅ You can complete all parts in 3 weeks at your current pace"

---

## Research Sources

1. **Cognitive Load Theory:** 10-15 min attention span, 30 min optimal
2. **Spaced Learning:** First review Day 2, then Day 7, then Day 30
3. **Study Hours:** 4-6 hours/week = high achievement
4. **Active Engagement:** 90% retention when learner participates actively

---

## Future Enhancements

- [ ] Track actual user completion times per part (refine estimates)
- [ ] A/B test different part counts (validate assumptions)
- [ ] Push notifications for spaced reviews ("Time to review Part 1!")
- [ ] Learning analytics dashboard ("You complete 80% of 3-part lessons")
- [ ] Adjust complexity based on quiz performance
