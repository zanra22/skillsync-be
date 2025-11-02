import json
import logging
import os
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
import uuid
import hashlib
import azure.functions as func
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger('azure')
logger.setLevel(logging.INFO)

class DatabaseManager:
    """Minimal database manager for Azure Functions (without Django ORM)"""

    def __init__(self):
        self.conn = None
        self.environment = os.getenv('ENVIRONMENT', 'development')

    def connect(self):
        """Establish database connection from environment variables"""
        try:
            if self.environment == 'development':
                self.conn = psycopg2.connect(
                    host=os.getenv('DEV_DB_HOST', 'localhost'),
                    port=os.getenv('DEV_DB_PORT', '5432'),
                    database=os.getenv('DEV_DB_NAME'),
                    user=os.getenv('DEV_DB_USER'),
                    password=os.getenv('DEV_DB_PASSWORD')
                )
            else:  # production
                self.conn = psycopg2.connect(
                    host=os.getenv('PROD_DB_HOST', 'localhost'),
                    port=os.getenv('PROD_DB_PORT', '5432'),
                    database=os.getenv('PROD_DB_NAME'),
                    user=os.getenv('PROD_DB_USER'),
                    password=os.getenv('PROD_DB_PASSWORD')
                )
            logger.info(f"[LessonOrchestrator] Connected to {self.environment} database")
        except Exception as e:
            logger.error(f"[LessonOrchestrator] Database connection failed: {e}")
            raise

    def execute(self, query, params=None):
        """Execute a query"""
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"[LessonOrchestrator] Query execution failed: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

db = DatabaseManager()

class LessonOrchestrationService:
    """Service to orchestrate lesson generation via Django GraphQL API"""

    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        # Get Django app URL based on environment (REQUIRED)
        if self.environment == 'production':
            self.django_api_url = os.getenv('PROD_DJANGO_URL')
        else:
            self.django_api_url = os.getenv('DEV_DJANGO_URL')

        if not self.django_api_url:
            raise ValueError(
                f"Django API URL not configured. "
                f"Please set {self.environment.upper()}_DJANGO_URL environment variable"
            )
        logger.info(f"[LessonOrchestrator] Django API URL: {self.django_api_url}")

    async def generate_lesson_via_api(self, message_data: dict) -> dict:
        """
        Call Django GraphQL API to generate a lesson for a module.

        This approach:
        1. Separates concerns (Azure Functions handles queuing, Django handles generation)
        2. Reuses existing lesson generation logic
        3. Allows Django to update module status atomically

        Args:
            message_data: Message from Service Bus containing module info

        Returns:
            dict: API response with generation status
        """
        try:
            module_id = message_data.get('module_id')
            logger.info(f"[LessonOrchestrator] Triggering lesson generation for module: {module_id}")

            # GraphQL mutation to generate module lessons
            graphql_query = """
            mutation GenerateModuleLessons($moduleId: String!) {
                lessons {
                    generateModuleLessons(moduleId: $moduleId) {
                        id
                        title
                        generationStatus
                        generationError
                        lessonsCount
                    }
                }
            }
            """

            payload = {
                "query": graphql_query,
                "variables": {
                    "moduleId": module_id
                }
            }

            logger.info(f"[LessonOrchestrator] Calling Django API: {self.django_api_url}")
            logger.debug(f"[LessonOrchestrator] Payload: {json.dumps(payload)}")

            # Call Django GraphQL endpoint
            response = requests.post(
                self.django_api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # 5 minute timeout for lesson generation
            )

            logger.info(f"[LessonOrchestrator] API response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[LessonOrchestrator] API response: {json.dumps(result)}")

                # Check for GraphQL errors
                if 'errors' in result:
                    logger.error(f"[LessonOrchestrator] GraphQL error: {result['errors']}")
                    return {
                        'success': False,
                        'error': f"GraphQL error: {result['errors']}",
                        'module_id': module_id
                    }

                return {
                    'success': True,
                    'data': result.get('data'),
                    'module_id': module_id
                }
            else:
                logger.error(f"[LessonOrchestrator] API request failed with status {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'module_id': module_id
                }

        except requests.exceptions.Timeout:
            logger.error(f"[LessonOrchestrator] API request timeout (lesson generation took too long)")
            return {
                'success': False,
                'error': "Timeout: lesson generation took too long",
                'module_id': message_data.get('module_id')
            }

        except Exception as e:
            logger.error(f"[LessonOrchestrator] Error calling Django API: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'module_id': message_data.get('module_id')
            }

lesson_service = LessonOrchestrationService()

async def main(lessonmessage: func.ServiceBusMessage, context: func.Context):
    """
    Azure Function triggered by Service Bus messages.
    Processes lesson generation requests via Django GraphQL API.

    ARCHITECTURE:
    1. Service Bus receives message from Django (module_id, user_profile, etc.)
    2. Azure Function parses message
    3. Azure Function calls Django GraphQL API to generate lessons
    4. Django handles all lesson generation (AI, research, DB updates)
    5. Azure Function logs the result

    This separation allows:
    - Reliable message queuing (Service Bus)
    - Async processing (Azure Functions)
    - Reusable AI logic (Django app)
    - Atomic DB updates (Django)
    """
    db_connection = None

    try:
        # ============================================
        # STEP 1: Parse the Service Bus message
        # ============================================
        message_body = lessonmessage.get_body().decode('utf-8')
        message_data = json.loads(message_body)

        module_id = message_data.get('module_id', 'unknown')
        title = message_data.get('title', 'Unknown Module')

        logger.info(f"[LessonOrchestrator] ========================================")
        logger.info(f"[LessonOrchestrator] Processing module: {module_id}")
        logger.info(f"[LessonOrchestrator] Title: {title}")
        logger.info(f"[LessonOrchestrator] Message timestamp: {message_data.get('timestamp', 'N/A')}")

        # ============================================
        # STEP 2: Connect to database
        # ============================================
        db.connect()
        db_connection = db
        logger.info(f"[LessonOrchestrator] Database connected")

        # ============================================
        # STEP 3: Update module status to 'in_progress'
        # ============================================
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            cursor = db.execute(
                """UPDATE lessons_module
                   SET generation_status=%s, generation_started_at=%s
                   WHERE id=%s""",
                ('in_progress', current_time, module_id)
            )
            logger.info(f"[LessonOrchestrator] Module status updated to 'in_progress'")
        except Exception as e:
            logger.warning(f"[LessonOrchestrator] Could not update module status: {e}")

        # ============================================
        # STEP 4: Call Django GraphQL API to generate lessons
        # ============================================
        logger.info(f"[LessonOrchestrator] Calling Django API to generate lessons...")
        api_result = await lesson_service.generate_lesson_via_api(message_data)

        if not api_result.get('success'):
            logger.error(f"[LessonOrchestrator] Lesson generation failed: {api_result.get('error')}")

            # Update module status to 'failed' with error message
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                error_msg = api_result.get('error', 'Unknown error')
                cursor = db.execute(
                    """UPDATE lessons_module
                       SET generation_status=%s, generation_error=%s, generation_completed_at=%s
                       WHERE id=%s""",
                    ('failed', error_msg[:500], current_time, module_id)
                )
                logger.info(f"[LessonOrchestrator] Module status updated to 'failed'")
            except Exception as e:
                logger.error(f"[LessonOrchestrator] Could not update module status to failed: {e}")

            # Don't re-raise - let Service Bus handle retry/dead-letter
            return

        # ============================================
        # STEP 5: Verify lessons were created
        # ============================================
        try:
            cursor = db.execute(
                """SELECT COUNT(*) as lesson_count
                   FROM lessons_lessoncontent
                   WHERE module_id=%s""",
                (module_id,)
            )
            result = cursor.fetchone()
            lesson_count = result['lesson_count'] if result else 0
            logger.info(f"[LessonOrchestrator] ✅ Lessons created: {lesson_count}")

            # Update module status to 'completed'
            current_time = datetime.now(timezone.utc).isoformat()
            cursor = db.execute(
                """UPDATE lessons_module
                   SET generation_status=%s, generation_completed_at=%s
                   WHERE id=%s""",
                ('completed', current_time, module_id)
            )
            logger.info(f"[LessonOrchestrator] Module status updated to 'completed'")

        except Exception as e:
            logger.error(f"[LessonOrchestrator] Error verifying lessons: {e}")
            raise

        logger.info(f"[LessonOrchestrator] ✅ Successfully processed module: {module_id}")
        logger.info(f"[LessonOrchestrator] ========================================")

    except json.JSONDecodeError as e:
        logger.error(f"[LessonOrchestrator] ❌ Invalid JSON in message: {e}")
        # Don't re-raise - message will be dead-lettered

    except Exception as e:
        logger.error(f"[LessonOrchestrator] ❌ Error processing message: {e}", exc_info=True)
        # Don't re-raise - message will be dead-lettered

    finally:
        # ============================================
        # CLEANUP: Close database connection
        # ============================================
        if db_connection:
            try:
                db_connection.disconnect()
                logger.info(f"[LessonOrchestrator] Database connection closed")
            except Exception as e:
                logger.error(f"[LessonOrchestrator] Error closing database connection: {e}")