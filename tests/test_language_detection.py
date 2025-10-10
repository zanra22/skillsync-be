"""
Test Language Detection Enhancement

Tests the improved language/category detection with:
1. Broader keyword coverage
2. No default language assumption
3. 'general' category for non-programming topics

Author: SkillSync Team
Date: October 9, 2025
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from helpers.ai_lesson_service import LessonGenerationService

def test_language_detection():
    """Test language detection across various topics"""
    
    service = LessonGenerationService()
    
    test_cases = [
        # Python ecosystem
        {"topic": "Python Variables", "expected_lang": "python", "expected_cat": "python"},
        {"topic": "Django Models", "expected_lang": "python", "expected_cat": "python"},
        {"topic": "FastAPI Tutorial", "expected_lang": "python", "expected_cat": "python"},
        
        # JavaScript ecosystem
        {"topic": "JavaScript Functions", "expected_lang": "javascript", "expected_cat": "javascript"},
        {"topic": "Node.js Express Routes", "expected_lang": "javascript", "expected_cat": "javascript"},
        {"topic": "NPM Package Management", "expected_lang": "javascript", "expected_cat": "javascript"},
        
        # React/Frontend
        {"topic": "React Hooks", "expected_lang": "jsx", "expected_cat": "react"},
        {"topic": "Vue Components", "expected_lang": "vue", "expected_cat": "vue"},
        {"topic": "Angular Services", "expected_lang": "typescript", "expected_cat": "angular"},  # ✅ Angular uses TypeScript
        {"topic": "Next.js Routing", "expected_lang": "javascript", "expected_cat": "nextjs"},
        
        # TypeScript
        {"topic": "TypeScript Generics", "expected_lang": "typescript", "expected_cat": "typescript"},
        
        # Other languages
        {"topic": "Java Classes", "expected_lang": "java", "expected_cat": "java"},
        {"topic": "Go Goroutines", "expected_lang": "go", "expected_cat": "go"},
        {"topic": "Rust Ownership", "expected_lang": "rust", "expected_cat": "rust"},
        {"topic": "C++ Pointers", "expected_lang": "cpp", "expected_cat": "general"},  # No C++ category (use general)
        {"topic": "PHP Laravel Routes", "expected_lang": "php", "expected_cat": "php"},
        {"topic": "Ruby on Rails Models", "expected_lang": "ruby", "expected_cat": "ruby"},
        {"topic": "Swift SwiftUI Views", "expected_lang": "swift", "expected_cat": "swift"},
        {"topic": "Kotlin Coroutines", "expected_lang": "kotlin", "expected_cat": "kotlin"},
        
        # Web technologies
        {"topic": "HTML5 Semantic Tags", "expected_lang": "html", "expected_cat": "html"},
        {"topic": "CSS Flexbox Layout", "expected_lang": "css", "expected_cat": "css"},
        {"topic": "Tailwind CSS Utilities", "expected_lang": "css", "expected_cat": "css"},
        
        # Databases
        {"topic": "SQL Joins", "expected_lang": "sql", "expected_cat": "sql"},
        {"topic": "PostgreSQL Indexes", "expected_lang": "sql", "expected_cat": "sql"},
        {"topic": "MongoDB Aggregation", "expected_lang": None, "expected_cat": "mongodb"},
        
        # DevOps
        {"topic": "Docker Containers", "expected_lang": None, "expected_cat": "docker"},
        {"topic": "Kubernetes Pods", "expected_lang": None, "expected_cat": "kubernetes"},
        {"topic": "Git Branching", "expected_lang": None, "expected_cat": "git"},
        
        # Shell scripting
        {"topic": "Bash Scripting", "expected_lang": "shell", "expected_cat": "general"},
        {"topic": "PowerShell Commands", "expected_lang": "powershell", "expected_cat": "general"},
        
        # 🎯 NEW: Topics with NO language (should return None, not Python!)
        {"topic": "Project Management Basics", "expected_lang": None, "expected_cat": "general"},
        {"topic": "Agile Methodology", "expected_lang": None, "expected_cat": "general"},
        {"topic": "Data Structures Overview", "expected_lang": None, "expected_cat": "general"},
        {"topic": "Algorithm Design", "expected_lang": None, "expected_cat": "general"},
        {"topic": "Software Architecture", "expected_lang": None, "expected_cat": "general"},
    ]
    
    print("=" * 100)
    print("  LANGUAGE DETECTION TEST")
    print("=" * 100)
    print()
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        topic = test["topic"]
        expected_lang = test["expected_lang"]
        expected_cat = test["expected_cat"]
        
        detected_lang = service._infer_language(topic)
        detected_cat = service._infer_category(topic)
        
        lang_match = detected_lang == expected_lang
        cat_match = detected_cat == expected_cat
        
        if lang_match and cat_match:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"{status} | {topic:<35} | Lang: {str(detected_lang):<15} Cat: {detected_cat:<15}")
        
        if not lang_match:
            print(f"       Expected language: {expected_lang}, Got: {detected_lang}")
        if not cat_match:
            print(f"       Expected category: {expected_cat}, Got: {detected_cat}")
    
    print()
    print("=" * 100)
    print(f"  RESULTS: {passed}/{len(test_cases)} passed ({(passed/len(test_cases)*100):.1f}%)")
    print("=" * 100)
    print()
    
    # Key improvements to highlight
    print("🎯 KEY IMPROVEMENTS:")
    print()
    print("1. ✅ No default language assumption")
    print("   - 'Project Management' → None (not forced to Python)")
    print("   - 'Algorithm Design' → None (not forced to Python)")
    print()
    print("2. ✅ Broader language support")
    print("   - Added: SQL, Java, Go, Rust, PHP, Ruby, Swift, Kotlin")
    print("   - Added: HTML, CSS, Shell, PowerShell")
    print()
    print("3. ✅ Better framework detection")
    print("   - React, Vue, Angular, Next.js")
    print("   - Django, Flask, FastAPI, Laravel, Rails")
    print()
    print("4. ✅ DevOps tool detection")
    print("   - Docker, Kubernetes, Git")
    print()
    print("5. ✅ Database support")
    print("   - SQL, PostgreSQL, MySQL, MongoDB")
    print()
    
    if failed > 0:
        print(f"⚠️  {failed} tests failed. Review detection logic above.")
    else:
        print("🎉 All tests passed! Language detection is working perfectly!")
    
    return passed == len(test_cases)


if __name__ == "__main__":
    success = test_language_detection()
    sys.exit(0 if success else 1)
