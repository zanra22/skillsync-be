# SkillSync Subscription & Community Ecosystem Model

**Status:** DRAFT Proposal
**Objective:** Define the logic for community-driven content reuse and the tier-based access model for Learners and Mentors.

---

## 1. The "Community-First" Content Engine

To reduce AI costs and foster a shared knowledge base, SkillSync prioritizes existing high-quality content over generating new content match-for-match.

### The Flow: "Search, Suggest, Then Generate"

When a user requests a new Roadmap (e.g., "Python Basics"):

1.  **Semantic Search & Match**:
    *   System embeds the user's request (Skill: "Python", Level: "Beginner", Goal: "Data Science").
    *   Queries the `Roadmap` database for existing public roadmaps.
    *   **Matching Criteria**:
        *   **Relevance Score**: > 85% match on skills/topics.
        *   **Quality Threshold**: Must have > X Upvotes or be "Mentor Verified".
        *   **Suitability**: Matches user's time commitment (e.g., "10 hours/week").

2.  **The "fork" Option (Suggestion Phase)**:
    *   *If matches found*: Present the user with "Verified Community Roadmaps".
        *   "We found a highly-rated 'Python for Data Science' roadmap utilized by 500 learners. Would you like to use this?"
    *   *Incentive*: "Using this roadmap grants you 50 Community Credits" (gamification hook).

3.  **Generation (Fallback)**:
    *   *If NO matches found* OR *User rejects suggestions*:
    *   Proceed to specific AI generation via the Hybrid System.
    *   New roadmap becomes part of the public pool (unless User is Enterprise/Private).

### Granularity: Modules & Lessons

*   **Modules**: If a user creates a custom roadmap but needs a standarized module (e.g., "Python Lists"), check if a "Gold Standard" module for "Python Lists" exists. Reuse it by reference.
*   **Lessons**: Before generating "Intro to Variables", check if we have a lesson with:
    *   High completion rate (>80%).
    *   Positive sentiment/Upvotes.
    *   Recent update (< 6 months).

---

## 2. The Reputation & Review Economy

To ensure quality, not everyone can influence the platform equally. We distinguish between **Signals** (Votes) and **Reviews** (Text).

### Who Can Vote (Upvote/Downvote)?
*   **Requirement**: Must have **Added** the Roadmap/Module to their library AND completed at least **10%** of it.
*   *Justification*: Prevents "blind voting" and spam.

### Who Can Leave Written Reviews?
*   **Requirement**:
    *   **Learners**: Must have completed **30%** of the content OR hold a **Level 1+ Subscription**.
    *   **Mentors**: Can review any content (Expert Review).
*   *Justification*: High-quality feedback comes from engaged users or experts.

---

## 3. Subscription Tiers: Learners

We propose a "pay-for-capacity + verification" model.

| Feature | **Free Tier** | **Level 1 (Plus)** | **Level 2 (Pro)** |
| :--- | :--- | :--- | :--- |
| **Active Roadmaps** | **1** Active Roadmap | **3** Active Roadmaps | **Unlimited** |
| **AI Generation** | Standard Queue (Slower) | Priority Queue | Priority Queue + Better Models (e.g., Claude 3.5 Sonnet) |
| **Review Rights** | Completion-gated | Immediate Access | Immediate Access |
| **Community** | Read-only Comments | Comment & Discuss | Create Study Groups |
| **Verification** | Standard Profile | "Supporter" Badge | "Pro" Badge |
| **Certificates** | None | **Verified Completion Certs** (Shareable) | **Verified Completion Certs** |
| **Analytics** | Basic Progress % | **Learning Velocity & Peer Stats** | **Predictive Mastery AI** |
| **Privacy** | Public Only | Public Only | **Private Roadmaps** (Not shared) |
| **Career** | None | **AI Resume Builder** (from skills) | **Priority Job Nominations** |

*   **Active Roadmap**: A roadmap currently in progress. Users can "Archive" old ones to free up slots.

---

## 4. Subscription Tiers: Mentors

Mentors are the backbone of verification. **Crucially, "Verified" status cannot be bought.** It must be earned through activity or credentials.

| Feature | **Standard Mentor** | **Verified Mentor (Tier 1)** | **Expert Mentor (Tier 2)** |
| :--- | :--- | :--- | :--- |
| **Verification** | Email Verified | **Activity Verified** (Blue Check) | **Credential Verified** (Gold Check) |
| **Requirements** | None (Open to all) | **>50 Active Mentees** + 4.5★ Rating | **Masters/PhD** OR **>500 Active Mentees** |
| **Subscription Cost**| Free | $ Paid (Optional for Tools) | $ Paid (Optional for Tools) |
| **Visibility** | Searchable | Featured in Results | "SkillSync Recommended" |
| **Commission** | 15% Platform Fee | 10% Platform Fee | 5% Platform Fee |
| **Content** | Can create Public Roadmaps | "Verified" badge on Roadmaps | Can sell Premium Modules |

---

## 5. Mentor Verification Pathways

We believe in two paths to mentorship: **Organic Growth** (proving yourself on the platform) and **Credentialed Entry** (proving your real-world expertise).

### Pathway A: Organic Growth (From Learner to Mentor)
*   **Target**: Learners who mastered skills on SkillSync.
*   **Requirements**:
    1.  **Completion**: Finished **5+ Roadmaps** in a specific domain.
    2.  **Contribution**: Provided **10+ Accepted Solutions** in community discussions.
    3.  **Reputation**: Maintain a "Helpful" score of >80%.
*   *Reward*: Unlocks "Standard Mentor" status automatically.

### Pathway B: Credentialed Entry (Direct Application)
*   **Target**: Industry professionals and academics.
*   **Requirements**:
    *   Upload Proof of **Master's Degree / PhD** in relevant field.
    *   OR upload **Professional Certification** (e.g., AWS Professional, CPA).
    *   OR link **LinkedIn Profile** with >5 years experience (manual review).
*   *Reward*: Unlocks "Expert Mentor" status after manual review.

---

## 5. Technical Implications

### Backend Changes
*   **`Vote` Model**: `user`, `content_type`, `object_id`, `score (+1/-1)`.
*   **`Review` Model**: Text content, rating (1-5), tied to `Vote`.
*   **Matching Engine**: New service `helpers/roadmap_matcher.py` to calculate similarity scores using vector embeddings (e.g., `pgvector`).
*   **Subscription Enforcement**: Middleware/Decorator `@check_subscription_limit('roadmaps')`.

### Frontend Changes
*   **Suggestion UI**: "Before we generate..." modal showing matching community roadmaps.
*   **Voting UI**: Upvote/Downvote buttons on Match/Module/Lesson cards.
*   **Tier Gates**: visual indicators for "Upgrade to add more roadmaps".

---

## 6. Implementation Stages (Draft)

1.  **Stage 1**: Database schema for Voting/Subscription limits.
2.  **Stage 2**: The "Matcher" service (simple keyword match first, vector later).
3.  **Stage 3**: Integrating the "Suggestion" flow into the Roadmap Creation Wizard.
4.  **Stage 4**: Subscription payment integration (Stripe) & Tier enforcement.
