# Lesson Generation Testing Plan

## Overview
After modularization, we need to verify that lesson generation works correctly in both local and production environments.

## Testing Checklist

### Phase 1: Module Import Testing ✅ DONE
- [x] AI providers module imports
- [x] Lesson generators module imports
- [x] Utilities module imports
- [x] All 4 learning style generators import

### Phase 2: Local Testing (TODO - NEEDS TO RUN)

#### 2.1: Direct Service Testing
```bash
python test_lesson_generation.py
```
**What it does:**
- Initializes LessonGenerationService
- Tests each of 4 learning styles (hands_on, video, reading, mixed)
- Verifies basic lesson structure
- Checks for required fields
- Output: JSON results file

**Expected results:**
- All 4 tests should PASS
- Each lesson should have: title, summary, type/lesson_type
- No import errors
- No API errors (if keys configured)

#### 2.2: Database Integration Testing
```bash
python test_lesson_generation_local.py --list-modules --email test@example.com
python test_lesson_generation_local.py --test-function --module-id <MODULE_ID>
```
**What it does:**
- Tests with actual database
- Tests with real user profile
- Tests Azure Function simulation
- Verifies lesson storage

**Expected results:**
- Lessons created in database
- Correct module assigned
- All 4 learning styles work

### Phase 3: Production Testing (TODO - NEEDS MANUAL VERIFICATION)

#### 3.1: Via GraphQL API
```graphql
# From frontend or GraphQL Playground
mutation GenerateLesson {
  generateLessonMutation(
    moduleId: "..."
    learningStyle: "hands_on"
  ) {
    success
    lessonId
    message
  }
}
```

#### 3.2: Via Service Bus / Azure Functions
- Trigger module generation
- Monitor Azure Functions logs
- Verify lessons appear in database

### Phase 4: Regression Testing (TODO)

#### 4.1: YouTube Service Integration
- [ ] YouTube video search works
- [ ] Quality ranking still applied
- [ ] Transcript fetching (captions + Groq fallback)
- [ ] Video analysis generates study guides

#### 4.2: Multi-Source Research
- [ ] Research data integration
- [ ] Multiple API calls work (if enabled)
- [ ] Attribution stored correctly

#### 4.3: All Features Still Work
- [ ] Lesson duration calculation
- [ ] User profile context applied
- [ ] Content complexity adjustment
- [ ] Diagram generation
- [ ] Image generation
- [ ] JSON parsing/repair

## Test Files Available

1. **test_lesson_generation.py** - Quick module test (we just created)
2. **test_lesson_generation_local.py** - Full integration test (existing)
3. **test_trigger_lesson_generation.py** - Service Bus/Azure Functions test
4. **test_complete_onboarding_flow.py** - End-to-end flow test

## Running Tests Locally

### Prerequisites
```bash
cd skillsync-be
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Setup
```bash
# Create .env file with:
GEMINI_API_KEY=...
YOUTUBE_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
UNSPLASH_ACCESS_KEY=...
```

### Run Tests
```bash
# Quick module import test
python test_lesson_generation.py

# Full database integration test (requires Django/PostgreSQL)
python test_lesson_generation_local.py --test-function --module-id abc123
```

## Success Criteria

### All tests should:
✅ Complete without errors
✅ Generate valid JSON lesson data
✅ Include all required fields
✅ Work for all 4 learning styles
✅ Create lessons in database (integration test)
✅ Maintain backward compatibility
✅ Show no performance degradation

### No tests should:
❌ Have import errors
❌ Timeout (>5 min per lesson)
❌ Lose any functionality
❌ Break existing integrations
❌ Create invalid data in database

## Rollback Plan

If tests fail:
1. Identify which learning style fails
2. Check error logs
3. If critical: revert commit `d8547f0`
4. Debug in isolation
5. Re-commit when fixed

## Next Steps After Testing

1. ✅ Run test_lesson_generation.py locally
2. ✅ Verify no errors for all 4 styles
3. ✅ Run test_lesson_generation_local.py with real data
4. ✅ Confirm lessons created correctly
5. ✅ Create refactor/modularize-lesson-service branch
6. ✅ Begin Phase 2 work
