# 🎯 SkillSync Content Generation Master Plan

**Date Created**: October 8, 2025  
**Version**: 1.0  
**Status**: Phase 1 - Foundation & Content Generation

---

## 📋 Executive Summary

SkillSync will implement an **AI-powered, community-curated learning content system** that:
- Generates personalized lessons based on user learning styles
- Leverages free-tier APIs (Gemini, YouTube, Unsplash) for cost efficiency
- Implements smart caching with community validation for quality assurance
- Achieves 99.9% cost savings through content reuse
- Provides multiple content versions per topic for user choice

**Target**: Serve 50K+ users/month on free tier with 80%+ cache hit rate

---

## 🎨 Core Learning Styles (4 Approaches)

### 1. **Hands-on Projects 🛠️** (70% practice, 30% theory)
**Target Users**: Builders, coders, kinesthetic learners

**Content Structure**:
- Brief text explanations (200-300 words per concept)
- 3-4 coding exercises per lesson (progressive difficulty)
- Starter code templates
- Expected outputs for validation
- Progressive hints system (3 levels)
- Capstone project per roadmap step
- Auto-grading logic (output comparison)

**Tools & APIs**:
- Gemini 1.5 Flash (text generation) - FREE tier: 1,500 RPM
- Monaco Editor (in-browser code editor) - FREE
- Mermaid.js (diagrams) - FREE
- Optional: Pyodide (Python in browser) or Backend sandbox

**Cost per Lesson**: ~$0.03 (cacheable)

---

### 2. **Video Tutorials 🎥** (Content curation + AI analysis)
**Target Users**: Visual learners, video-preferred students

**Content Structure**:
```
Step 1: YouTube API searches best tutorial
Step 2: Fetch video transcript (YouTube Transcript API)
Step 3: Gemini analyzes transcript to generate:
    ├─ Lesson summary (3-4 sentences)
    ├─ Key concepts (5-7 bullet points)
    ├─ Timestamped study guide (jump to sections)
    ├─ Important moments with context
    └─ Quiz based on video content (5-7 questions)
Step 4: Embed video player with AI-generated notes
```

**User Options**:
- Read AI summary (quick overview)
- Watch full video (deep learning)
- Jump to timestamps (specific topics)
- Must pass quiz (80%+) to proceed

**Tools & APIs**:
- YouTube Data API v3 - FREE (10K requests/day)
- YouTube Transcript API (python library) - FREE
- Gemini 1.5 Flash (transcript analysis) - FREE tier
- Video.js or native HTML5 player - FREE

**Cost per Lesson**: ~$0.03 (cacheable)

**Filter Criteria for YouTube Videos**:
- Duration: 4-20 minutes (medium length)
- Quality: HD/High definition only
- Relevance: Sort by relevance score
- Language: English (configurable)
- Captions: Must have subtitles/transcript

---

### 3. **Reading & Research 📚** (90% text, 10% visuals)
**Target Users**: Deep learners, researchers, text-preferred students

**Content Structure**:
- Long-form text (2,000-3,000 words per lesson)
  - In-depth explanations with examples
  - Real-world case studies
  - Industry-specific applications
  - Best practices & anti-patterns
  - Common pitfalls & troubleshooting
- Visual aids:
  - Mermaid.js diagrams (flowcharts, graphs, hierarchies)
  - Concept maps
  - Comparison tables
- Hero images (Unsplash API)
- Comprehension quiz (10-12 deep questions)

**Tools & APIs**:
- Gemini 1.5 Flash (long-form generation) - FREE tier
- Mermaid.js (diagram rendering) - FREE
- Unsplash API (stock images) - FREE (50 requests/hour)
- Markdown renderer (client-side) - FREE

**Cost per Lesson**: ~$0.05 (cacheable)

---

### 4. **Mix of Everything 🎨** (Balanced approach)
**Target Users**: Flexible learners, comprehensive coverage seekers

**Content Distribution**:
- 30% Text lessons (Gemini theory)
- 30% Video tutorials (YouTube + analysis)
- 20% Hands-on exercises (coding projects)
- 10% Infographics (Mermaid.js diagrams)
- 10% Quizzes & assessments

**Example Lesson Flow**:
```
1. Text Introduction (5 min read) - Concept overview
2. Mermaid.js Diagram - Visual representation
3. YouTube Video (10-15 min) - Expert explanation
4. AI Study Guide - Key takeaways from video
5. Coding Exercise - Practical application
6. Quiz (5-7 questions) - Knowledge validation
```

**Cost per Lesson**: ~$0.07 (cacheable)

---

## 🗄️ Database Architecture

### **Model 1: LessonContent**
```python
class LessonContent(models.Model):
    """Stores individual lesson content versions"""
    
    # Identification
    roadmap_step_title = CharField(max_length=255)  # "Python Variables"
    lesson_number = IntegerField()  # 1, 2, 3...
    learning_style = CharField(max_length=50)  # hands_on, video, reading, mixed
    
    # Content (flexible JSON structure)
    content = JSONField()  # Lesson data: text, exercises, videos, etc.
    
    # Metadata
    title = CharField(max_length=255)
    description = TextField()
    estimated_duration = IntegerField()  # minutes
    difficulty_level = CharField(max_length=20)  # beginner/intermediate/advanced
    
    # AI Generation Info
    generated_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    generated_at = DateTimeField(auto_now_add=True)
    generation_prompt = TextField()  # Debug/audit trail
    ai_model_version = CharField(max_length=50)  # "gemini-1.5-flash-2024-10"
    
    # Community Feedback
    upvotes = IntegerField(default=0)
    downvotes = IntegerField(default=0)
    approval_status = CharField(
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Community Approved'),
            ('rejected', 'Community Rejected'),
            ('mentor_verified', 'Mentor Verified')
        ],
        default='pending'
    )
    
    # Quality Metrics
    view_count = IntegerField(default=0)
    completion_rate = FloatField(default=0.0)  # % who finish
    average_quiz_score = FloatField(default=0.0)  # Learning effectiveness
    
    # Caching
    cache_key = CharField(max_length=255, db_index=True)  # MD5 hash
    
    # Computed Properties
    @property
    def net_votes(self):
        return self.upvotes - self.downvotes
    
    @property
    def approval_rate(self):
        total = self.upvotes + self.downvotes
        return (self.upvotes / total * 100) if total > 0 else 0
```

### **Model 2: LessonVote**
```python
class LessonVote(models.Model):
    """Track individual user votes on lessons"""
    
    user = ForeignKey(User, on_delete=CASCADE)
    lesson_content = ForeignKey(LessonContent, on_delete=CASCADE)
    vote_type = CharField(
        max_length=10,
        choices=[('upvote', 'Upvote'), ('downvote', 'Downvote')]
    )
    comment = TextField(blank=True)  # Optional feedback
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'lesson_content']  # One vote per user
```

### **Model 3: UserRoadmapLesson**
```python
class UserRoadmapLesson(models.Model):
    """Maps user's roadmap to specific lesson content versions"""
    
    user = ForeignKey(User, on_delete=CASCADE)
    roadmap_step = ForeignKey('RoadmapStep', on_delete=CASCADE)
    lesson_number = IntegerField()
    
    # Which version user is using
    lesson_content = ForeignKey(LessonContent, on_delete=SET_NULL, null=True)
    
    # Progress tracking
    status = CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        default='not_started'
    )
    
    # Performance metrics
    quiz_score = IntegerField(null=True)
    exercises_completed = IntegerField(default=0)
    time_spent = IntegerField(default=0)  # minutes
    
    # Timestamps
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    
    class Meta:
        unique_together = ['user', 'roadmap_step', 'lesson_number']
```

### **Model 4: MentorReview**
```python
class MentorReview(models.Model):
    """Mentor-specific reviews (higher weight than community votes)"""
    
    mentor = ForeignKey(User, on_delete=CASCADE, limit_choices_to={'role': 'mentor'})
    lesson_content = ForeignKey(LessonContent, on_delete=CASCADE)
    
    status = CharField(
        max_length=20,
        choices=[
            ('verified', 'Verified Correct'),
            ('needs_improvement', 'Needs Improvement'),
            ('rejected', 'Rejected')
        ]
    )
    
    feedback = TextField()  # Detailed mentor feedback
    expertise_area = CharField(max_length=100)  # "Python Programming"
    reviewed_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['mentor', 'lesson_content']
```

---

## 🧠 Smart Content Selection Algorithm

### **LessonSelector Service**

```python
class LessonSelector:
    """
    Intelligent lesson content selector.
    Prioritizes community-approved, falls back to generation.
    """
    
    def get_or_generate_lesson(step_title, lesson_num, style, user):
        """Main entry point"""
        
        # 1. Check for existing approved lessons
        existing = find_existing_lessons(step_title, lesson_num, style)
        
        if existing.exists():
            # Return best lesson (community-validated)
            best = select_best_lesson(existing)
            best.view_count += 1
            best.save()
            
            logger.info(f"✅ Reusing lesson ID {best.id} (+{best.net_votes} votes)")
            return best
        
        # 2. No approved lesson → Generate new
        logger.info(f"🤖 Generating new lesson for {step_title}")
        new_lesson = generate_new_lesson(step_title, lesson_num, style, user)
        
        return new_lesson
    
    def select_best_lesson(lessons):
        """
        Score lessons based on multiple factors:
        - Community votes (+10 points per net vote)
        - Mentor verification (+500 bonus)
        - Completion rate (+100 points max)
        - Quiz performance (+5 points per %)
        - Recency (up to +30 for new content)
        """
        
        scored = []
        for lesson in lessons:
            score = 0
            score += lesson.net_votes * 10
            score += 500 if lesson.approval_status == 'mentor_verified' else 0
            score += lesson.completion_rate * 100
            score += lesson.average_quiz_score * 5
            
            days_old = (now() - lesson.generated_at).days
            score += max(0, 30 - days_old)
            
            scored.append((lesson, score))
        
        return max(scored, key=lambda x: x[1])[0]
```

---

## 💰 Cost Analysis

### **Gemini API Free Tier Limits**:
- **Requests per minute**: 15 RPM
- **Requests per day**: 1,500 RPD
- **Tokens per minute**: 1M TPM
- **Monthly cost**: $0

### **Cost per Generation**:
- Roadmap: ~$0.001 (2K tokens)
- Hands-on lesson: ~$0.03 (3K tokens)
- Video analysis: ~$0.03 (5K input + 3K output)
- Reading lesson: ~$0.05 (3K tokens, longer)
- Mixed lesson: ~$0.07 (combined)

### **With Community Caching**:
```
Scenario: 100,000 users learn "Python Basics" (30 lessons each)

WITHOUT Caching:
- 100,000 × 30 lessons × $0.03 = $90,000

WITH Caching (80% hit rate):
- First 100 users generate: 30 × $0.03 × 100 = $90
- Next 99,900 users reuse: $0
- Total: $90 for 100K users = $0.0009 per user
- Savings: 99.9% 🔥
```

### **Free Tier Capacity**:
```
Daily capacity: 1,500 requests
If 80% are cached hits:
= 1,500 / 0.2 = 7,500 effective lessons/day
= 225,000 lessons/month
= ~50,000 users/month (assuming 4.5 lessons per user)

Conclusion: Free tier sufficient for MVP phase (0-50K users)
```

---

## 🎯 Auto-Approval Criteria

Lessons auto-approve when ALL criteria met:

```python
AUTO_APPROVE_THRESHOLD = {
    'min_votes': 10,              # At least 10 total votes
    'approval_rate': 0.80,        # 80%+ upvotes
    'min_completions': 20,        # 20+ users finished
    'min_completion_rate': 0.70,  # 70%+ finish rate
    'min_quiz_score': 60.0,       # 60%+ avg quiz score
}

# Mentor verification = instant approval (+500 quality bonus)
```

---

## 🚀 Phase 1 Implementation Plan (Weeks 1-4)

### **Week 1: Database Foundation**
**Goal**: Set up all database models and migrations

- [ ] Create `LessonContent` model
- [ ] Create `LessonVote` model
- [ ] Create `UserRoadmapLesson` model
- [ ] Create `MentorReview` model
- [ ] Add database indexes for performance
- [ ] Create GraphQL types for all models
- [ ] Run migrations and test schema

**Deliverable**: Working database schema with test data

---

### **Week 2: Core Content Generation**
**Goal**: Build lesson generation service for all 4 learning styles

- [ ] Create `LessonGenerationService` class
- [ ] Implement hands-on lesson generator
  - [ ] Text explanations generator
  - [ ] Coding exercise generator
  - [ ] Hint system generator
  - [ ] Starter code template generator
- [ ] Implement video lesson generator
  - [ ] YouTube API integration (search)
  - [ ] YouTube Transcript API integration
  - [ ] Gemini transcript analysis
  - [ ] Timestamped study guide generator
- [ ] Implement reading lesson generator
  - [ ] Long-form text generator
  - [ ] Mermaid.js diagram syntax generator
  - [ ] Unsplash API integration
- [ ] Implement mixed lesson generator
  - [ ] Combine all 4 approaches
  - [ ] Balance content distribution
- [ ] Add error handling and fallbacks
- [ ] Create prompt templates for each style

**Deliverable**: Fully functional lesson generation system

---

### **Week 3: Smart Selection & Caching**
**Goal**: Implement intelligent lesson selection and caching

- [ ] Create `LessonSelector` service
- [ ] Implement cache key generation (MD5 hash)
- [ ] Build `find_existing_lessons()` method
- [ ] Build `select_best_lesson()` scoring algorithm
- [ ] Implement `generate_new_lesson()` with caching
- [ ] Add `regenerate_lesson()` for alternatives
- [ ] Create quality metrics updater
- [ ] Add auto-approval logic
- [ ] Implement rate limiting (15 RPM for Gemini)
- [ ] Add request queue system

**Deliverable**: Smart caching system that prioritizes community-approved content

---

### **Week 4: GraphQL API Layer**
**Goal**: Expose content generation via GraphQL

- [ ] Create `getLessonContent` query
  - [ ] Fetch lesson by ID
  - [ ] Include vote counts, metrics, status
- [ ] Create `getOrGenerateLesson` query
  - [ ] Smart selection logic
  - [ ] Cache-first approach
- [ ] Create `voteLesson` mutation
  - [ ] Upvote/downvote logic
  - [ ] Update approval status
  - [ ] Check auto-approval criteria
- [ ] Create `regenerateLesson` mutation
  - [ ] Generate alternative version
  - [ ] Keep old version in DB
  - [ ] Update user's roadmap
- [ ] Create `getLessonVersions` query
  - [ ] Show all versions for a topic
  - [ ] Sort by votes/quality
- [ ] Add authentication checks
- [ ] Add rate limiting middleware
- [ ] Write API documentation

**Deliverable**: Complete GraphQL API for content generation

---

## 🧪 Testing Strategy

### **Unit Tests**:
- [ ] Test each lesson generator (hands-on, video, reading, mixed)
- [ ] Test cache key generation
- [ ] Test scoring algorithm
- [ ] Test auto-approval logic
- [ ] Test vote counting

### **Integration Tests**:
- [ ] Test full lesson generation flow
- [ ] Test caching behavior (hit/miss scenarios)
- [ ] Test YouTube API integration
- [ ] Test Gemini API integration
- [ ] Test GraphQL mutations/queries

### **Manual Testing**:
- [ ] Generate 10 lessons per learning style (40 total)
- [ ] Verify content quality
- [ ] Check API response times (<3 seconds)
- [ ] Test with different user profiles
- [ ] Validate caching behavior

---

## 📊 Success Metrics (Phase 1)

### **Technical Metrics**:
- ✅ All 4 learning styles generate successfully
- ✅ Cache hit rate >80% after 100 lessons generated
- ✅ API response time <3 seconds (cached) / <15 seconds (generation)
- ✅ Zero rate limit errors with queue system
- ✅ Database queries <50ms (with indexes)

### **Quality Metrics**:
- ✅ Generated content passes manual review (10 samples)
- ✅ Video lessons include accurate timestamps
- ✅ Code exercises are syntactically correct
- ✅ Quizzes are relevant to lesson content
- ✅ Mermaid.js diagrams render correctly

### **Cost Metrics**:
- ✅ Stay within Gemini free tier (1,500 RPD)
- ✅ Zero YouTube API charges
- ✅ Zero Unsplash API charges
- ✅ Total API cost: $0/month

---

## 🔒 Security & Best Practices

### **API Security**:
- Store API keys in environment variables (never commit)
- Use `.env` files with `.gitignore`
- Rotate API keys quarterly
- Monitor API usage (alert if approaching limits)

### **Content Safety**:
- Sanitize all AI-generated content (XSS prevention)
- Validate YouTube video IDs (prevent injection)
- Filter inappropriate content (Gemini safety settings)
- Add content moderation for community votes

### **Rate Limiting**:
- Queue requests when approaching 15 RPM
- Show loading indicators to users (10-15 seconds)
- Implement exponential backoff on errors
- Cache aggressively to minimize API calls

### **Database Performance**:
- Add indexes on cache_key, approval_status, upvotes
- Use `select_related` for foreign keys
- Implement database connection pooling
- Monitor slow queries (>100ms)

---

## 📝 Environment Variables Required

```bash
# Backend (.env)
GEMINI_API_KEY=your_gemini_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here

# Optional (for caching)
REDIS_URL=redis://localhost:6379
```

---

## 🎯 Phase 1 Completion Checklist

Before moving to Phase 2, ensure:

- [ ] All 4 database models created and migrated
- [ ] All 4 lesson generators working (hands-on, video, reading, mixed)
- [ ] Smart caching system implemented
- [ ] Community voting system functional
- [ ] Auto-approval logic working
- [ ] GraphQL API complete and documented
- [ ] Rate limiting prevents API quota issues
- [ ] Cache hit rate >80% after 100 lessons
- [ ] Manual testing of 40 lessons (10 per style) passed
- [ ] All environment variables configured
- [ ] Security best practices implemented
- [ ] Code reviewed and approved
- [ ] Documentation complete

---

## 🚀 Next Steps (Phase 2 Preview)

After Phase 1 completion, we'll build:

1. **Frontend Components** (Week 5-6)
   - Lesson viewer UI
   - Voting interface
   - "Generate Alternative" button
   - Progress tracking dashboard

2. **Code Execution** (Week 7-8) - Hands-on only
   - Monaco Editor integration
   - Pyodide (Python in browser) OR backend sandbox
   - Exercise submission system
   - Auto-grading logic

3. **Mentor Features** (Week 9-10)
   - Mentor review interface
   - Quality assurance dashboard
   - Content moderation tools

4. **Analytics & Optimization** (Week 11-12)
   - Lesson performance metrics
   - User engagement tracking
   - A/B testing framework
   - Content recommendation engine

---

## 📚 Additional Resources

### **API Documentation**:
- [Gemini API Docs](https://ai.google.dev/docs)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [YouTube Transcript API](https://pypi.org/project/youtube-transcript-api/)
- [Unsplash API](https://unsplash.com/documentation)
- [Mermaid.js Docs](https://mermaid.js.org/)

### **Libraries & Tools**:
- Django 5.2+
- Strawberry GraphQL
- youtube-transcript-api
- requests (HTTP client)
- hashlib (cache keys)
- Redis (optional caching layer)

---

**Document Version**: 1.0  
**Last Updated**: October 8, 2025  
**Next Review**: After Phase 1 completion  
**Owner**: SkillSync Development Team
