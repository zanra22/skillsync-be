# 🔑 API Keys Setup Guide for Lesson Generation

## Required API Keys

### 1. ✅ Gemini API (Already Configured)
- **Status**: ✅ Found in `.env`
- **Key**: `GEMINI_API_KEY=AIzaSy...`
- **No action needed**

---

### 2. 🎥 YouTube Data API v3 (Optional but Recommended)

#### Get Your API Key:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **YouTube Data API v3**: https://console.cloud.google.com/apis/library/youtube.googleapis.com
4. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
5. Click **Create Credentials** → **API Key**
6. Copy the API key

#### Add to `.env`:
```bash
YOUTUBE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

#### Free Tier Limits:
- ✅ **10,000 requests per day** (FREE)
- Each video search = ~100 quota units
- ~100 searches per day free

#### What if I don't add it?
- Video lessons will still work
- Will use **fallback mode**: generates text-based lessons without real videos
- Gemini will create sample video descriptions

---

### 3. 🖼️ Unsplash API (Optional)

#### Get Your Access Key:
1. Go to [Unsplash Developers](https://unsplash.com/developers)
2. Sign up or log in
3. Click **New Application**
4. Accept terms → Create application
5. Copy **Access Key**

#### Add to `.env`:
```bash
UNSPLASH_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Free Tier Limits:
- ✅ **50 requests per hour** (FREE)
- ✅ **5,000 requests per month** (FREE)

#### What if I don't add it?
- Reading lessons will still work
- Will use **fallback**: No hero images, or generic placeholder images

---

## 🚀 Quick Setup (Copy-Paste)

Add these lines to your `.env` file:

```bash
# ========================================
# AI CONTENT GENERATION
# ========================================

# Gemini API (REQUIRED - already configured ✅)
GEMINI_API_KEY=AIzaSyCUi1eU4gu40F8mreCItC0rfprwFTt5e6M

# YouTube API (Optional - for video lessons)
YOUTUBE_API_KEY=your-youtube-api-key-here

# Unsplash API (Optional - for hero images)
UNSPLASH_ACCESS_KEY=your-unsplash-access-key-here
```

---

## 🧪 Testing Without Optional APIs

You can test the lesson generation system **right now** with just Gemini:

```bash
python test_lesson_generation.py
```

**Expected Results**:
- ✅ Hands-on lessons: Will work (uses Gemini only)
- ⚠️ Video lessons: Will work in fallback mode (no real YouTube videos)
- ✅ Reading lessons: Will work (no hero images)
- ✅ Mixed lessons: Will work (combines all)

---

## 📊 Cost Comparison

| API | Free Tier | Cost After Free Tier | Recommendation |
|-----|-----------|---------------------|----------------|
| **Gemini** | 1,500 req/day | $0.075/1M tokens | ✅ Required |
| **YouTube** | 10K req/day | $0 (no paid tier) | ⭐ Highly recommended |
| **Unsplash** | 50 req/hour | $0 (no paid tier) | Optional |

**Total Cost**: $0 for all 3 APIs at current scale! 🎉

---

## ✅ Recommended Setup Priority

### Phase 1: MVP (Now)
- ✅ Gemini API only
- Test all 4 lesson types in fallback mode
- Validate lesson quality

### Phase 2: Video Enhancement (This Week)
- Add YouTube API key
- Enable real video search
- Test video transcript analysis

### Phase 3: Visual Polish (Next Week)
- Add Unsplash API key
- Add hero images to reading lessons
- Final polish

---

## 🎯 Next Steps

1. **Option A - Test Now (Gemini Only)**:
   ```bash
   python test_lesson_generation.py
   ```

2. **Option B - Add YouTube API First**:
   - Get YouTube API key (5 minutes)
   - Add to `.env`
   - Run test script

3. **Option C - Add All APIs**:
   - Get YouTube + Unsplash keys (10 minutes)
   - Add both to `.env`
   - Run full test

**Recommendation**: Start with Option A to validate the system works, then add APIs as needed.

---

Need help getting API keys? Let me know which one you want to set up first!
