# src/personal_assistant/crud/crud_conversation.py
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json

from ..models.database import Conversation as ConversationModel # Alias to avoid naming conflict

def create_conversation_entry(db: Session, *, user_id: str, message: str, response_data: Dict) -> ConversationModel:
    """
    Saves a user message and the assistant's response dictionary to the database.
    Extracts the actual response text if possible.
    """
    # Try to extract the main response text for storage, fallback to full JSON if needed
    response_text = response_data.get("response", json.dumps(response_data))
    if isinstance(response_text, dict): # Handle cases where response itself is a dict
        response_text = json.dumps(response_text)

    db_obj = ConversationModel(
        user_id=user_id,
        message=message,
        response=response_text # Store the extracted response or the JSON dict
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_conversation_history(db: Session, *, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Retrieves the last N conversation turns (user message + assistant response)
    and formats them as a list of {"role": "...", "content": "..."} dicts.
    """
    history_orm = (
        db.query(ConversationModel)
        .filter(ConversationModel.user_id == user_id)
        .order_by(ConversationModel.created_at.desc())
        .limit(limit * 2) # Fetch potentially more to ensure we get pairs
        .all()
    )

    # Format into user/assistant pairs, starting with the oldest in the limit
    formatted_history = []
    # Iterate in reverse order (oldest first) to build the history chronologically
    for entry in reversed(history_orm):
         # Ensure we don't add duplicate roles consecutively if data is messy
         # Although, based on create_conversation_entry, this shouldn't happen.
         if entry.message:
             formatted_history.append({"role": "user", "content": entry.message})
         if entry.response:
              # Attempt to parse response if it was stored as JSON, otherwise use as is
             try:
                 # Check if it looks like a JSON object/array before parsing
                 if entry.response.strip().startswith("{") or entry.response.strip().startswith("["):
                     response_content = json.loads(entry.response)
                     # Extract meaningful text if possible (e.g., from {"response": "text"})
                     if isinstance(response_content, dict) and "response" in response_content:
                          response_text = str(response_content["response"])
                     else:
                          response_text = json.dumps(response_content) # Fallback to stringified JSON
                 else:
                     response_text = entry.response # Treat as plain text
             except json.JSONDecodeError:
                 response_text = entry.response # Fallback to using the raw string

             formatted_history.append({"role": "assistant", "content": response_text})

    # Ensure we return the correct number of turns (pairs) if limit matters strictly elsewhere
    # For LLM history, returning the full fetched pairs is usually fine.
    # Limit based on total items, roughly limiting turns.
    return formatted_history[-limit*2:] # Return the last N *pairs* (approx) 