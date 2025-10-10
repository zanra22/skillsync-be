"""
Django Admin configuration for Lesson Content models.
"""

from django.contrib import admin
from .models import LessonContent, LessonVote, UserRoadmapLesson, MentorReview


@admin.register(LessonContent)
class LessonContentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'roadmap_step_title', 'lesson_number', 
        'learning_style', 'approval_status', 'net_votes', 
        'view_count', 'generated_at'
    ]
    list_filter = ['learning_style', 'approval_status', 'difficulty_level']
    search_fields = ['title', 'roadmap_step_title', 'cache_key']
    readonly_fields = ['cache_key', 'generated_at', 'net_votes', 'approval_rate', 'days_old']
    ordering = ['-upvotes', '-generated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('roadmap_step_title', 'lesson_number', 'learning_style', 'cache_key')
        }),
        ('Content', {
            'fields': ('title', 'description', 'content', 'estimated_duration', 'difficulty_level')
        }),
        ('AI Generation', {
            'fields': ('generated_by', 'generated_at', 'generation_prompt', 'ai_model_version')
        }),
        ('Community Feedback', {
            'fields': ('upvotes', 'downvotes', 'approval_status', 'net_votes', 'approval_rate')
        }),
        ('Quality Metrics', {
            'fields': ('view_count', 'completion_rate', 'average_quiz_score', 'days_old')
        }),
    )


@admin.register(LessonVote)
class LessonVoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'lesson_content', 'vote_type', 'created_at']
    list_filter = ['vote_type', 'created_at']
    search_fields = ['user__email', 'lesson_content__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(UserRoadmapLesson)
class UserRoadmapLessonAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'roadmap_step_title', 'lesson_number', 
        'status', 'quiz_score', 'exercises_completed', 'completed_at'
    ]
    list_filter = ['status', 'roadmap_step_title']
    search_fields = ['user__email', 'roadmap_step_title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['user', 'roadmap_step_title', 'lesson_number']


@admin.register(MentorReview)
class MentorReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'mentor', 'lesson_content', 'status', 
        'expertise_area', 'reviewed_at'
    ]
    list_filter = ['status', 'expertise_area', 'reviewed_at']
    search_fields = ['mentor__email', 'lesson_content__title', 'expertise_area']
    readonly_fields = ['reviewed_at', 'updated_at']
    ordering = ['-reviewed_at']
