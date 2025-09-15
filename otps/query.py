import strawberry
import strawberry_django
from typing import List, Optional
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import TrustedDevice
from .types import TrustedDeviceType

User = get_user_model()


@strawberry.type
class OTPQuery:
    """GraphQL queries for OTP operations"""

    @strawberry.field
    async def user_trusted_devices(self, user_id: str) -> List[TrustedDeviceType]:
        """
        Get all trusted devices for a user.
        
        Args:
            user_id: User ID to get devices for
            
        Returns:
            List[TrustedDeviceType]: List of trusted devices
        """
        try:
            user = await sync_to_async(User.objects.get)(id=user_id)
            devices = await sync_to_async(list)(
                TrustedDevice.objects.filter(
                    user=user,
                    is_active=True
                ).order_by('-last_used')
            )
            
            return devices
            
        except User.DoesNotExist:
            return []
        except Exception:
            return []

    @strawberry.field
    async def trusted_device_by_id(self, device_id: str) -> Optional[TrustedDeviceType]:
        """
        Get a specific trusted device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Optional[TrustedDeviceType]: Trusted device if found
        """
        try:
            device = await sync_to_async(TrustedDevice.objects.get)(
                id=device_id,
                is_active=True
            )
            return device
            
        except TrustedDevice.DoesNotExist:
            return None
        except Exception:
            return None
