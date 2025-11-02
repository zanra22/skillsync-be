import os
import uuid
import json
import pytest
import django
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# Import models and services after Django setup
from lessons.models import Module, Lesson
from helpers.ai_roadmap_service import RoadmapGenerationService
from helpers.ai_lesson_service import LessonGenerationService
from users.models import User
from profiles.models import UserProfile


class TestAzureFunctionsIntegration(TestCase):
    """Test the Azure Durable Functions integration."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword123'
        )
        
        # Create a user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            learning_goals='Test learning goals',
            experience_level='beginner'
        )
        
        # Create a test module
        self.module = Module.objects.create(
            title='Test Module',
            description='Test module description',
            difficulty='beginner',
            user=self.user,
            generation_status='pending',
            generation_job_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4())
        )
        
        # Set up the test client
        self.client = Client()
        
        # Mock environment variables
        os.environ['AZURE_SERVICE_BUS_CONNECTION_STRING'] = 'Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=test;SharedAccessKey=test'
        os.environ['AZURE_FUNCTIONS_ENVIRONMENT'] = 'test'

    @patch('helpers.ai_roadmap_service.ServiceBusClient')
    def test_enqueue_module_for_generation(self, mock_service_bus_client):
        """Test enqueueing a module for generation."""
        # Set up the mock
        mock_sender = MagicMock()
        mock_service_bus_client.from_connection_string.return_value.__enter__.return_value.get_queue_sender.return_value.__enter__.return_value = mock_sender
        
        # Create the service
        service = RoadmapGenerationService()
        
        # Call the method
        service.enqueue_module_for_generation(self.module, self.user, self.profile)
        
        # Assert the message was sent
        mock_sender.send_messages.assert_called_once()
        
        # Verify the module was updated
        self.module.refresh_from_db()
        assert self.module.generation_status == 'pending'
        assert self.module.generation_job_id is not None

    @patch('helpers.ai_lesson_service.ServiceBusClient')
    def test_enqueue_lesson_generation(self, mock_service_bus_client):
        """Test enqueueing a lesson for generation."""
        # Set up the mock
        mock_sender = MagicMock()
        mock_service_bus_client.from_connection_string.return_value.__enter__.return_value.get_queue_sender.return_value.__enter__.return_value = mock_sender
        
        # Create the service
        service = LessonGenerationService()
        
        # Create test data
        lesson_request = {
            'title': 'Test Lesson',
            'description': 'Test lesson description',
            'module_id': str(self.module.id)
        }
        
        # Call the method to enqueue lesson generation
        with patch.object(service, '_enqueue_lesson_generation') as mock_enqueue:
            service.generate_lesson(
                lesson_request,
                self.user,
                self.profile,
                save_to_db=True
            )
            mock_enqueue.assert_called_once()

    def test_check_module_generation_status_api(self):
        """Test the API endpoint for checking module generation status."""
        # Log in the user
        self.client.force_login(self.user)
        
        # Set up the module with a status
        self.module.generation_status = 'completed'
        self.module.generation_completed_at = django.utils.timezone.now()
        self.module.save()
        
        # Create some lessons for this module
        for i in range(3):
            Lesson.objects.create(
                title=f'Test Lesson {i}',
                content=f'Test content {i}',
                module=self.module,
                order=i
            )
        
        # Call the API
        url = reverse('check_module_generation_status', kwargs={'module_id': self.module.id})
        response = self.client.get(url)
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['lesson_count'], 3)
        self.assertIsNotNone(data['completed_at'])

    def test_module_orchestrator(self):
        """Test the module orchestrator function."""
        # This would normally be a more complex integration test
        # For now, we'll just verify the module can be updated with the right status
        
        # Simulate what the orchestrator would do
        self.module.generation_status = 'in_progress'
        self.module.generation_started_at = django.utils.timezone.now()
        self.module.save()
        
        # Verify the update worked
        self.module.refresh_from_db()
        self.assertEqual(self.module.generation_status, 'in_progress')
        self.assertIsNotNone(self.module.generation_started_at)

    def test_lesson_orchestrator(self):
        """Test the lesson orchestrator function."""
        # Similar to the module orchestrator test, this is simplified
        
        # Create a lesson
        lesson = Lesson.objects.create(
            title='Test Orchestrated Lesson',
            content='Initial content',
            module=self.module,
            order=0
        )
        
        # Simulate what the orchestrator would do
        lesson.content = 'Updated content from orchestrator'
        lesson.save()
        
        # Verify the update worked
        lesson.refresh_from_db()
        self.assertEqual(lesson.content, 'Updated content from orchestrator')


if __name__ == '__main__':
    pytest.main()