import strawberry
from .query import AdminQuery
from .mutation import AdminMutation

# Admin schema that combines queries and mutations
admin_schema = strawberry.Schema(
    query=AdminQuery,
    mutation=AdminMutation
)
