import strawberry
import strawberry_django
from typing import List, Optional
from django.contrib.auth import get_user_model
from .models import TrustedDevice
from .types import TrustedDeviceType

User = get_user_model()


@strawberry.type
class OTPQuery:
    """GraphQL queries for OTP operations"""

    @strawberry.field
    def user_trusted_devices(self, user_id: str) -> List[TrustedDeviceType]:
        """
        Get all trusted devices for a user.
        
        Args:
            user_id: User ID to get devices for
            
        Returns:
            List[TrustedDeviceType]: List of trusted devices
        """
        try:
            user = User.objects.get(id=user_id)
            devices = TrustedDevice.objects.filter(
                user=user,
                is_active=True
            ).order_by('-last_used')
            
            return devices
            
        except User.DoesNotExist:
            return []
        except Exception:
            return []

    @strawberry.field
    def trusted_device_by_id(self, device_id: str) -> Optional[TrustedDeviceType]:
        """
        Get a specific trusted device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Optional[TrustedDeviceType]: Trusted device if found
        """
        try:
            device = TrustedDevice.objects.get(
                id=device_id,
                is_active=True
            )
            return device
            
        except TrustedDevice.DoesNotExist:
            return None
        except Exception:
            return None
