from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Module

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def check_module_generation_status(request, module_id):
    """
    API endpoint to check the generation status of a module.
    Returns the current status, error message (if any), and timestamps.
    """
    try:
        # Get the module
        module = await Module.objects.filter(id=module_id).afirst()
        
        if not module:
            return Response(
                {"error": f"Module with ID {module_id} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the user has access to this module
        if str(module.roadmap.user_id) != str(request.user.id):
            return Response(
                {"error": "You do not have permission to access this module"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Return the status
        return Response({
            "module_id": module.id,
            "title": module.title,
            "generation_status": module.generation_status,
            "generation_error": module.generation_error,
            "generation_started_at": module.generation_started_at,
            "generation_completed_at": module.generation_completed_at,
            "lessons_count": await module.lessoncontent_set.acount()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error checking module status: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )