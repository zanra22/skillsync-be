from django.urls import path
from . import api

urlpatterns = [
    # API endpoint for checking module generation status
    path('api/modules/<uuid:module_id>/generation-status/', api.check_module_generation_status, name='check_module_generation_status'),
]