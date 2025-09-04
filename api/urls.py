from ninja import NinjaAPI
from .schema import schema # Import the schema you just created

from strawberry.django.views import AsyncGraphQLView

api = NinjaAPI()

# Add a path for the GraphQL view
api.add_router("/", AsyncGraphQLView.as_view(schema=schema))