"""
Test: Fetch and Display Roadmaps, Modules, and Lessons

This script fetches all roadmaps from the database and displays their modules and lessons.
Usage:
    python test_fetch_roadmaps_modules_lessons.py
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import Roadmap, Module, LessonContent


def display_roadmaps():
    print("\n=== All Roadmaps ===\n")
    for roadmap in Roadmap.objects.all():
        print(f"Roadmap: {roadmap.title} (ID: {roadmap.id})")
        modules = Module.objects.filter(roadmap=roadmap).order_by('order')
        print(f"  Modules count: {modules.count()}")
        for module in modules:
            print(f"    Module: {module.title} (ID: {module.id})")
            lessons = LessonContent.objects.filter(module=module).order_by('lesson_number')
            print(f"      Lessons count: {lessons.count()}")
            for lesson in lessons:
                print(f"        Lesson {lesson.lesson_number}: {lesson.title} (ID: {lesson.id})")
                print(f"          Difficulty: {getattr(lesson, 'difficulty_level', '-')}")
                print(f"          Estimated Duration: {getattr(lesson, 'estimated_duration', '-')}")
                print(f"          Description: {getattr(lesson, 'description', '')[:100]}")
    print("\n=== End ===\n")

if __name__ == "__main__":
    display_roadmaps()
