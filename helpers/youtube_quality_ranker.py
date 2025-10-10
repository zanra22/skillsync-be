"""
YouTube Quality Ranking Service

Ranks YouTube videos based on multiple quality factors:
- View count (30%) - Popular videos likely better quality
- Like ratio (25%) - High like/dislike ratio = good content  
- Channel authority (20%) - Verified channels with subscribers
- Transcript quality (15%) - Clear, topic-relevant content
- Recency (10%) - Not too old, not too new

Replaces the current "first available" approach with intelligent ranking.
"""

import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class YouTubeQualityRanker:
    """
    Ranks YouTube videos based on quality factors.
    Returns best videos for educational content.
    """
    
    # Quality thresholds
    MIN_VIEW_COUNT = 10000  # Minimum 10K views
    MIN_LIKE_RATIO = 0.90  # Minimum 90% positive
    MIN_CHANNEL_SUBSCRIBERS = 50000  # 50K+ subscribers preferred
    OPTIMAL_AGE_MIN_MONTHS = 6  # Videos 6 months - 3 years old are optimal
    OPTIMAL_AGE_MAX_MONTHS = 36
    
    # Score weights
    WEIGHT_VIEWS = 0.30
    WEIGHT_LIKES = 0.25
    WEIGHT_CHANNEL = 0.20
    WEIGHT_TRANSCRIPT = 0.15
    WEIGHT_RECENCY = 0.10
    
    def __init__(self):
        pass
    
    def rank_videos(
        self,
        videos: List[Dict],
        topic: str,
        max_results: int = 3
    ) -> List[Dict]:
        """
        Rank videos by quality and return top N.
        
        Args:
            videos: List of video metadata dicts
            topic: Search topic (for transcript relevance)
            max_results: Number of top videos to return
            
        Returns:
            List of ranked videos with scores
        """
        if not videos:
            logger.warning("⚠️ No videos to rank")
            return []
        
        logger.info(f"📊 Ranking {len(videos)} videos for topic: {topic}")
        
        # Calculate score for each video
        scored_videos = []
        for video in videos:
            try:
                score = self._calculate_quality_score(video, topic)
                video['quality_score'] = score
                video['quality_breakdown'] = video.get('_quality_breakdown', {})
                scored_videos.append(video)
                
                logger.debug(
                    f"   Video: {video.get('title', 'Unknown')[:50]}... "
                    f"Score: {score:.2f}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to score video: {e}")
                continue
        
        # Sort by score (highest first)
        ranked_videos = sorted(
            scored_videos,
            key=lambda v: v['quality_score'],
            reverse=True
        )
        
        # Return top N
        top_videos = ranked_videos[:max_results]
        
        if top_videos:
            logger.info(
                f"✅ Top video: {top_videos[0]['title'][:50]}... "
                f"(Score: {top_videos[0]['quality_score']:.2f})"
            )
        
        return top_videos
    
    def _calculate_quality_score(
        self,
        video: Dict,
        topic: str
    ) -> float:
        """
        Calculate overall quality score (0-100).
        
        Score = (views * 0.30) + (likes * 0.25) + (channel * 0.20) + 
                (transcript * 0.15) + (recency * 0.10)
        """
        breakdown = {}
        
        # 1. View count score (0-100)
        view_score = self._calculate_view_score(video)
        breakdown['views'] = view_score
        
        # 2. Like ratio score (0-100)
        like_score = self._calculate_like_score(video)
        breakdown['likes'] = like_score
        
        # 3. Channel authority score (0-100)
        channel_score = self._calculate_channel_score(video)
        breakdown['channel'] = channel_score
        
        # 4. Transcript quality score (0-100)
        transcript_score = self._calculate_transcript_score(video, topic)
        breakdown['transcript'] = transcript_score
        
        # 5. Recency score (0-100)
        recency_score = self._calculate_recency_score(video)
        breakdown['recency'] = recency_score
        
        # Weighted sum
        total_score = (
            view_score * self.WEIGHT_VIEWS +
            like_score * self.WEIGHT_LIKES +
            channel_score * self.WEIGHT_CHANNEL +
            transcript_score * self.WEIGHT_TRANSCRIPT +
            recency_score * self.WEIGHT_RECENCY
        )
        
        # Store breakdown for debugging
        video['_quality_breakdown'] = breakdown
        
        return round(total_score, 2)
    
    def _calculate_view_score(self, video: Dict) -> float:
        """
        Score based on view count (normalized).
        
        10K views = 0 points
        100K views = 50 points
        1M+ views = 100 points
        """
        view_count = video.get('view_count', 0)
        
        if view_count < self.MIN_VIEW_COUNT:
            return 0.0  # Below minimum threshold
        
        # Logarithmic scale (views grow exponentially)
        import math
        
        # 10K = 0, 100K = 50, 1M = 100
        if view_count >= 1000000:
            return 100.0
        elif view_count >= 100000:
            # 100K-1M: Linear 50-100
            return 50 + (50 * (view_count - 100000) / 900000)
        else:
            # 10K-100K: Linear 0-50
            return 50 * (view_count - 10000) / 90000
    
    def _calculate_like_score(self, video: Dict) -> float:
        """
        Score based on like/dislike ratio.
        
        Like ratio = likes / (likes + dislikes)
        
        Note: YouTube removed dislike counts, so we estimate:
        - If only likes available: Assume 95% like ratio (good)
        - Use engagement rate as proxy
        """
        like_count = video.get('like_count', 0)
        view_count = video.get('view_count', 1)  # Avoid division by zero
        
        # Calculate engagement rate (likes / views)
        engagement_rate = like_count / view_count
        
        # Good engagement: 2-5% (typical for educational content)
        # Great engagement: 5-10%
        # Excellent engagement: 10%+
        
        if engagement_rate >= 0.10:  # 10%+ = excellent
            return 100.0
        elif engagement_rate >= 0.05:  # 5-10% = great
            return 70 + (30 * (engagement_rate - 0.05) / 0.05)
        elif engagement_rate >= 0.02:  # 2-5% = good
            return 40 + (30 * (engagement_rate - 0.02) / 0.03)
        elif engagement_rate >= 0.01:  # 1-2% = ok
            return 20 + (20 * (engagement_rate - 0.01) / 0.01)
        else:
            # Below 1% = poor engagement
            return 20 * (engagement_rate / 0.01)
    
    def _calculate_channel_score(self, video: Dict) -> float:
        """
        Score based on channel authority.
        
        Factors:
        - Subscriber count
        - Verified status
        - Channel age (if available)
        """
        subscriber_count = video.get('subscriber_count', 0)
        is_verified = video.get('is_verified', False)
        
        # Base score from subscribers
        if subscriber_count >= 1000000:  # 1M+
            base_score = 100.0
        elif subscriber_count >= 500000:  # 500K-1M
            base_score = 80 + (20 * (subscriber_count - 500000) / 500000)
        elif subscriber_count >= 100000:  # 100K-500K
            base_score = 60 + (20 * (subscriber_count - 100000) / 400000)
        elif subscriber_count >= self.MIN_CHANNEL_SUBSCRIBERS:  # 50K-100K
            base_score = 40 + (20 * (subscriber_count - 50000) / 50000)
        elif subscriber_count >= 10000:  # 10K-50K
            base_score = 20 + (20 * (subscriber_count - 10000) / 40000)
        else:  # < 10K
            base_score = 20 * (subscriber_count / 10000)
        
        # Bonus for verified channels (+10%)
        if is_verified:
            base_score = min(100.0, base_score * 1.10)
        
        return base_score
    
    def _calculate_transcript_score(
        self,
        video: Dict,
        topic: str
    ) -> float:
        """
        Score based on transcript quality.
        
        Factors:
        - Contains key topic terms
        - Clear language (low filler word ratio)
        - Good structure (has intro, body, conclusion patterns)
        - Length appropriate for topic
        """
        transcript = video.get('transcript_text', '')
        
        if not transcript:
            # No transcript = can't evaluate quality
            return 50.0  # Neutral score
        
        score = 0.0
        
        # 1. Topic relevance (40 points)
        # Extract key terms from topic
        topic_terms = self._extract_key_terms(topic)
        transcript_lower = transcript.lower()
        
        matches = sum(
            1 for term in topic_terms
            if term.lower() in transcript_lower
        )
        
        if topic_terms:
            relevance = (matches / len(topic_terms)) * 40
            score += relevance
        else:
            score += 20  # No terms to check, give partial credit
        
        # 2. Language clarity (30 points)
        # Low filler word ratio = clear communication
        filler_words = ['um', 'uh', 'like', 'you know', 'so', 'basically']
        word_count = len(transcript.split())
        filler_count = sum(
            transcript_lower.count(f' {filler} ')
            for filler in filler_words
        )
        
        if word_count > 0:
            filler_ratio = filler_count / word_count
            # Less than 5% fillers = excellent (30 pts)
            # 5-10% = good (20 pts)
            # 10%+ = poor (10 pts)
            if filler_ratio < 0.05:
                score += 30
            elif filler_ratio < 0.10:
                score += 20
            else:
                score += 10
        
        # 3. Structure quality (30 points)
        # Check for intro/conclusion patterns
        has_intro = any(
            phrase in transcript_lower[:500]
            for phrase in ['today', 'going to', 'will learn', 'welcome']
        )
        has_conclusion = any(
            phrase in transcript_lower[-500:]
            for phrase in ['summary', 'conclusion', 'learned', 'recap']
        )
        
        if has_intro:
            score += 15
        if has_conclusion:
            score += 15
        
        return min(100.0, score)
    
    def _calculate_recency_score(self, video: Dict) -> float:
        """
        Score based on video age.
        
        Optimal: 6 months - 3 years old
        - Recent enough to be relevant
        - Old enough to be tested/proven
        
        Too new (< 6 months): May have errors, not battle-tested
        Too old (> 3 years): May be outdated (especially for tech)
        """
        published_at = video.get('published_at')
        
        if not published_at:
            return 50.0  # Unknown age = neutral
        
        # Parse date
        try:
            if isinstance(published_at, str):
                pub_date = datetime.fromisoformat(
                    published_at.replace('Z', '+00:00')
                )
            else:
                pub_date = published_at
        except Exception:
            return 50.0
        
        # Calculate age in months
        age_days = (datetime.now(pub_date.tzinfo) - pub_date).days
        age_months = age_days / 30.44  # Average month length
        
        # Scoring curve
        if self.OPTIMAL_AGE_MIN_MONTHS <= age_months <= self.OPTIMAL_AGE_MAX_MONTHS:
            # Optimal range: 100 points
            return 100.0
        elif age_months < self.OPTIMAL_AGE_MIN_MONTHS:
            # Too new: Linear decrease
            # 0 months = 50 pts, 6 months = 100 pts
            return 50 + (50 * age_months / self.OPTIMAL_AGE_MIN_MONTHS)
        else:
            # Too old: Linear decrease
            # 3 years = 100 pts, 5 years = 50 pts, 10 years = 0 pts
            if age_months >= 120:  # 10+ years
                return 0.0
            else:
                # 36-120 months: 100 to 0
                return 100 - (100 * (age_months - 36) / 84)
    
    def _extract_key_terms(self, topic: str) -> List[str]:
        """
        Extract key terms from topic for relevance checking.
        
        Examples:
        - "Python Variables" → ["python", "variables", "variable"]
        - "JavaScript Functions" → ["javascript", "functions", "function"]
        - "React Hooks useState" → ["react", "hooks", "usestate"]
        """
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into',
            'introduction', 'lesson', 'tutorial', 'guide', 'basics'
        }
        
        # Split and clean
        words = re.findall(r'\b\w+\b', topic.lower())
        
        # Filter stop words and short words
        key_terms = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]
        
        # Add singular/plural variants
        expanded = []
        for term in key_terms:
            expanded.append(term)
            if term.endswith('s'):
                expanded.append(term[:-1])  # plural → singular
            else:
                expanded.append(term + 's')  # singular → plural
        
        return list(set(expanded))  # Remove duplicates
    
    def filter_by_quality_threshold(
        self,
        videos: List[Dict],
        min_score: float = 50.0
    ) -> List[Dict]:
        """
        Filter videos by minimum quality score.
        Useful for rejecting low-quality content.
        
        Args:
            videos: List of scored videos
            min_score: Minimum acceptable score (default 50)
            
        Returns:
            Filtered list of videos above threshold
        """
        return [
            video for video in videos
            if video.get('quality_score', 0) >= min_score
        ]
    
    def get_quality_summary(self, video: Dict) -> str:
        """
        Generate human-readable quality summary.
        
        Returns:
            String like "Excellent (87/100): High views, great engagement"
        """
        score = video.get('quality_score', 0)
        breakdown = video.get('_quality_breakdown', {})
        
        # Overall rating
        if score >= 80:
            rating = "Excellent"
        elif score >= 65:
            rating = "Good"
        elif score >= 50:
            rating = "Fair"
        else:
            rating = "Poor"
        
        # Identify strengths
        strengths = []
        if breakdown.get('views', 0) >= 70:
            strengths.append("high views")
        if breakdown.get('likes', 0) >= 70:
            strengths.append("great engagement")
        if breakdown.get('channel', 0) >= 70:
            strengths.append("trusted channel")
        if breakdown.get('transcript', 0) >= 70:
            strengths.append("quality content")
        if breakdown.get('recency', 0) >= 80:
            strengths.append("recent")
        
        strengths_str = ", ".join(strengths) if strengths else "basic quality"
        
        return f"{rating} ({score:.0f}/100): {strengths_str.capitalize()}"


# Singleton instance
youtube_quality_ranker = YouTubeQualityRanker()
