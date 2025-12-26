"""
Azure Function: Generate Single Lesson Content (On-Demand)

This function is triggered via HTTP POST to generate content for a single lesson skeleton.

Flow:
1. Receives lesson_id from HTTP request
2. Calls Django GraphQL mutation: generateLessonContent(lessonId)
3. Django generates full content and updates lesson status
4. Returns success/failure response

Trigger: HTTP POST
Endpoint: /api/generate_lesson_content
"""

import json
import logging
import os
import requests
import azure.functions as func

# Configure logging
logger = logging.getLogger('azure')
logger.setLevel(logging.INFO)


class LessonContentGenerator:
    """Service to generate single lesson content via Django GraphQL API"""

    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Get Django app URL based on environment
        if self.environment == 'production':
            self.django_api_url = os.getenv('PROD_DJANGO_URL')
        else:
            self.django_api_url = os.getenv('DEV_DJANGO_URL', 'http://localhost:8000')

        if not self.django_api_url:
            raise ValueError(
                f"Django API URL not configured. "
                f"Please set {self.environment.upper()}_DJANGO_URL environment variable"
            )
        
        # Remove trailing slash and /graphql/ if present to avoid duplication
        self.django_api_url = self.django_api_url.rstrip('/')
        if self.django_api_url.endswith('/graphql'):
            self.django_api_url = self.django_api_url[:-8]  # Remove '/graphql'
        
        self.graphql_endpoint = f"{self.django_api_url}/graphql/"
        logger.info(f"[GenerateLessonContent] Django GraphQL URL: {self.graphql_endpoint}")

    def generate_lesson_content(self, lesson_id: str, user_id: str) -> dict:
        """
        Call Django GraphQL API to generate content for a single lesson.

        Args:
            lesson_id: ID of the lesson skeleton to generate content for
            user_id: ID of the user who owns the lesson

        Returns:
            dict with success status and lesson data
        """
        logger.info(f"[GenerateLessonContent] Generating content for lesson: {lesson_id}")

        # GraphQL mutation (nested under 'lessons')
        mutation = """
        mutation GenerateLessonContent($lessonId: String!) {
            lessons {
                generateLessonContent(lessonId: $lessonId) {
                    id
                    title
                    generationStatus
                    generationError
                    content
                }
            }
        }
        """

        payload = {
            "query": mutation,
            "variables": {
                "lessonId": lesson_id
            }
        }

        headers = {
            "Content-Type": "application/json",
            "X-User-Id": user_id,  # Pass user ID for authentication
        }

        try:
            logger.info(f"[GenerateLessonContent] Calling Django API...")
            response = requests.post(
                self.graphql_endpoint,
                json=payload,
                headers=headers,
                timeout=300  # 5 minute timeout for lesson generation
            )

            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                logger.error(f"[GenerateLessonContent] GraphQL error: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "lesson_id": lesson_id
                }

            lesson_data = result["data"]["lessons"]["generateLessonContent"]
            logger.info(f"[GenerateLessonContent] ✅ Lesson generated successfully")
            logger.info(f"   Status: {lesson_data['generationStatus']}")
            logger.info(f"   Title: {lesson_data['title']}")

            return {
                "success": True,
                "lesson": lesson_data,
                "lesson_id": lesson_id
            }

        except requests.exceptions.Timeout:
            logger.error(f"[GenerateLessonContent] Request timeout after 5 minutes")
            return {
                "success": False,
                "error": "Request timeout",
                "lesson_id": lesson_id
            }
        except Exception as e:
            logger.error(f"[GenerateLessonContent] Failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "lesson_id": lesson_id
            }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point for single lesson content generation.

    Expected request body:
    {
        "lesson_id": "abc123",
        "user_id": "user_xyz"
    }
    """
    logger.info('[GenerateLessonContent] Function triggered')

    try:
        # Parse request body
        req_body = req.get_json()
        lesson_id = req_body.get('lesson_id')
        user_id = req_body.get('user_id')

        if not lesson_id:
            return func.HttpResponse(
                json.dumps({"success": False, "error": "lesson_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not user_id:
            return func.HttpResponse(
                json.dumps({"success": False, "error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"[GenerateLessonContent] Lesson ID: {lesson_id}")
        logger.info(f"[GenerateLessonContent] User ID: {user_id}")

        # Generate lesson content
        generator = LessonContentGenerator()
        result = generator.generate_lesson_content(lesson_id, user_id)

        if result["success"]:
            return func.HttpResponse(
                json.dumps(result),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps(result),
                status_code=500,
                mimetype="application/json"
            )

    except ValueError as e:
        logger.error(f"[GenerateLessonContent] Invalid request: {e}")
        return func.HttpResponse(
            json.dumps({"success": False, "error": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"[GenerateLessonContent] Unexpected error: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"success": False, "error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
