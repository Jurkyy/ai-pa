from fastapi import APIRouter

from personal_assistant.api.v1.endpoints import (
    auth,
    integrations,
    rag,
    conversation,
    # users,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["conversation"]) 

# TODO: Add users router
# api_router.include_router(users.router, prefix="/users", tags=["users"])