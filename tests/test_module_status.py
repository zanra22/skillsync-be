import os
import uuid
import django
from django.test import TestCase
from django.utils import timezone

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# Import models after Django setup
from lessons.models import Module
from users.models import User
from profiles.models import UserProfile


class TestModuleStatusTracking(TestCase):
    """Test the Module model changes for job tracking."""

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

    def test_module_status_fields(self):
        """Test that the Module model has the necessary status tracking fields."""
        # Create a test module with status fields
        job_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        started_at = timezone.now()
        
        module = Module.objects.create(
            title='Test Module',
            description='Test module description',
            difficulty='beginner',
            user=self.user,
            generation_status='pending',
            generation_job_id=job_id,
            generation_started_at=started_at,
            idempotency_key=idempotency_key
        )
        
        # Retrieve the module and verify fields
        saved_module = Module.objects.get(id=module.id)
        self.assertEqual(saved_module.generation_status, 'pending')
        self.assertEqual(saved_module.generation_job_id, job_id)
        self.assertEqual(saved_module.idempotency_key, idempotency_key)
        self.assertIsNotNone(saved_module.generation_started_at)
        
        # Test status update
        saved_module.generation_status = 'completed'
        saved_module.generation_completed_at = timezone.now()
        saved_module.save()
        
        # Verify updated status
        updated_module = Module.objects.get(id=module.id)
        self.assertEqual(updated_module.generation_status, 'completed')
        self.assertIsNotNone(updated_module.generation_completed_at)

    def test_module_error_tracking(self):
        """Test error tracking in the Module model."""
        # Create a module with an error
        module = Module.objects.create(
            title='Error Module',
            description='Module with generation error',
            difficulty='beginner',
            user=self.user,
            generation_status='failed',
            generation_error='Test error message'
        )
        
        # Verify error is saved
        saved_module = Module.objects.get(id=module.id)
        self.assertEqual(saved_module.generation_status, 'failed')
        self.assertEqual(saved_module.generation_error, 'Test error message')


if __name__ == '__main__':
    import pytest
    pytest.main()