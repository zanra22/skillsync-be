#!/usr/bin/env python
"""
Test actual lesson generation with YouTube video selection.
Tests the complete pipeline: topic -> YouTube video search -> lesson generation.
"""
import os
import sys
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
import django
django.setup()

from helpers.ai_lesson_service import LessonGenerationService, LessonRequest

print("=" * 100)
print("LESSON GENERATION WITH YOUTUBE VIDEO TEST")
print("=" * 100)

# Initialize lesson service
print("\n[INFO] Initializing LessonGenerationService...")
lesson_service = LessonGenerationService()

# Test topics
test_lessons = [
    {
        "title": "Python List Comprehension",
        "step_title": "Python Intermediate Concepts",
        "learning_style": "video",
        "difficulty": "intermediate",
    },
    {
        "title": "JavaScript Event Listeners",
        "step_title": "JavaScript DOM Manipulation",
        "learning_style": "hands_on",
        "difficulty": "beginner",
    },
    {
        "title": "React Hooks useEffect",
        "step_title": "React Advanced Patterns",
        "learning_style": "reading",
        "difficulty": "intermediate",
    },
    {
        "title": "SQL JOIN Operations",
        "step_title": "Database Query Optimization",
        "learning_style": "mixed",
        "difficulty": "intermediate",
    },
    {
        "title": "Docker Container Networking",
        "step_title": "Docker & Containerization",
        "learning_style": "video",
        "difficulty": "advanced",
    },
]

results = {
    "success": 0,
    "failed": 0,
    "details": []
}

async def test_lesson_generation():
    """Test lesson generation for multiple topics"""

    for idx, lesson_config in enumerate(test_lessons, 1):
        title = lesson_config["title"]
        step_title = lesson_config["step_title"]
        learning_style = lesson_config["learning_style"]
        difficulty = lesson_config["difficulty"]

        print(f"\n[{idx}/{len(test_lessons)}] Generating lesson: {title}")
        print(f"    Step: {step_title} | Style: {learning_style} | Difficulty: {difficulty}")
        print("    Status: ", end="", flush=True)

        try:
            # Create lesson request
            request = LessonRequest(
                title=title,
                step_title=step_title,
                learning_style=learning_style,
                difficulty=difficulty,
            )

            # Call the actual lesson generation
            lesson_content = await lesson_service.generate_lesson(request)

            if lesson_content:
                print("[OK] Generated successfully")

                # Check if lesson has content
                has_content = False
                content_length = 0
                
                if isinstance(lesson_content, dict):
                    has_content = bool(lesson_content.get('content') or lesson_content.get('introduction'))
                    content_length = len(str(lesson_content))
                elif isinstance(lesson_content, str):
                    has_content = len(lesson_content) > 50
                    content_length = len(lesson_content)

                if has_content:
                    print(f"    Content: {content_length} characters")
                    results["success"] += 1
                    results["details"].append({
                        "title": title,
                        "status": "success",
                        "content_length": content_length,
                    })
                else:
                    print("    [WARN] Generated but no meaningful content")
                    results["failed"] += 1
                    results["details"].append({
                        "title": title,
                        "status": "empty_content",
                    })
            else:
                print("[FAIL] No lesson content returned")
                results["failed"] += 1
                results["details"].append({
                    "title": title,
                    "status": "no_content",
                })

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}")
            print(f"    Message: {str(e)[:100]}")
            results["failed"] += 1
            results["details"].append({
                "title": title,
                "status": "error",
                "error": str(e)[:100],
            })

# Run the async test
print("\n[INFO] Starting lesson generation tests...\n")
asyncio.run(test_lesson_generation())

# Print summary
print(f"\n{'=' * 100}")
print("RESULTS SUMMARY")
print(f"{'=' * 100}\n")

total = results["success"] + results["failed"]
success_pct = (results["success"] / total * 100) if total > 0 else 0

print(f"Total Lessons Tested:    {total}")
print(f"[OK]   Successful:       {results['success']} ({success_pct:.1f}%)")
print(f"[FAIL] Failed:           {results['failed']}")

# Show details
print(f"\n{'=' * 100}")
print("DETAILED RESULTS")
print(f"{'=' * 100}\n")

for detail in results["details"]:
    title = detail["title"]
    status = detail["status"]

    if status == "success":
        print(f"[OK] {title}")
        print(f"     Content length: {detail.get('content_length', 0)} chars")
    elif status == "error":
        print(f"[ERROR] {title}")
        print(f"        {detail.get('error', 'Unknown error')}")
    else:
        print(f"[FAIL] {title} - {status}")

# Conclusion
print(f"\n{'=' * 100}")
print("CONCLUSION")
print(f"{'=' * 100}\n")

if success_pct == 100:
    print(f"[OK] PERFECT! 100% of lessons generated successfully!")
    print("     The end-to-end lesson generation pipeline is working correctly.")
elif success_pct >= 80:
    print(f"[GOOD] Good! {success_pct:.1f}% of lessons generated successfully.")
    print("       Most topics are working well.")
elif success_pct >= 60:
    print(f"[WARN] Partial success. {success_pct:.1f}% of lessons generated.")
    print("       Some topics may need debugging.")
else:
    print(f"[POOR] Low success rate: {success_pct:.1f}% of lessons generated.")
    print("       There are issues with the lesson generation pipeline.")

print()

# Cleanup
print("[INFO] Cleaning up async resources...")
asyncio.run(lesson_service.cleanup())
print("[OK] Done!")
