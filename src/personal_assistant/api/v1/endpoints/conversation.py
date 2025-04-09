from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy.orm import Session

from personal_assistant.core.security import get_current_user
from personal_assistant.db.session import get_db
from personal_assistant.core.llm import get_llm, BaseLLM
from personal_assistant.core.conversation import ConversationHandler

router = APIRouter()

# --- Initialize Conversation Handler (could be done differently, e.g., via dependency) ---
# Create LLM instance once here, or manage its lifecycle better if needed (e.g., app lifespan)
# For simplicity, we create it here. Ensure LLM provider (e.g., 'claude', 'openai') is configured.
try:
    llm_instance = get_llm() # Reads from config/env by default
    conversation_handler = ConversationHandler(llm=llm_instance)
except ValueError as e:
    # Handle case where LLM provider is not supported or configured
    print(f"FATAL: Could not initialize LLM for ConversationHandler: {e}")
    # Option 1: Disable conversation endpoint gracefully (difficult with FastAPI setup)
    # Option 2: Raise the error to prevent app startup (better for required components)
    # Option 3: Let it run but have the endpoint fail - chosen here
    llm_instance = None
    conversation_handler = None
# --- 

class ProcessRequest(BaseModel):
    text: str
    # Potentially add conversation_id later for history

class ProcessResponse(BaseModel):
    response: Dict[str, Any] # The dictionary returned by the handler

@router.post("/process", response_model=ProcessResponse)
async def process_message(
    request: ProcessRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
    # llm: BaseLLM = Depends(get_llm_dependency) # Alternative: Inject LLM via dependency
):
    """Process a natural language message using the ConversationHandler"""
    if not conversation_handler:
        raise HTTPException(status_code=503, detail="Conversation handler is not available due to configuration error.")
        
    if not request.text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    # Extract user_id from the token data (assuming it's stored in 'sub')
    user_id = current_user.get("sub")
    if not user_id:
        # This shouldn't happen if get_current_user works correctly
        raise HTTPException(status_code=401, detail="Could not identify user.")

    try:
        # Pass message, db session, and user_id to the handler
        result = await conversation_handler.process_message(request.text, db, user_id)
        return ProcessResponse(response=result)
    except Exception as e:
        # Catch-all for unexpected errors in handler
        print(f"Error in /process endpoint: {e}")
        # Consider more specific error handling
        raise HTTPException(status_code=500, detail=f"Internal server error processing message: {str(e)}")

# Register intent handlers
@conversation_handler.register_intent("schedule_meeting")
async def handle_schedule_meeting(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle meeting scheduling intent"""
    # This would integrate with calendar and messaging platforms
    return {
        "action": "schedule_meeting",
        "status": "success",
        "details": entities
    }

@conversation_handler.register_intent("send_message")
async def handle_send_message(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle message sending intent"""
    # This would integrate with messaging platforms
    return {
        "action": "send_message",
        "status": "success",
        "details": entities
    } 