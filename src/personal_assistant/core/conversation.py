from typing import List, Dict, Any, Literal, Optional, Union
from pydantic import BaseModel, Field
import json
from .llm import BaseLLM, get_llm # Import LLM base and factory
from .vector_store import PostgreSQLVectorStore # Needed for RAG
# Import integrations dynamically or have a registry?
from ..integrations.email import EmailIntegration # Example integration
from sqlalchemy.orm import Session # Needed for DB access
from langchain.embeddings import OpenAIEmbeddings # Needed for RAG embeddings
from ..core.config import settings # For API keys
# Import CRUD operations
from ..crud import crud_conversation

# --- Define potential outputs for the LLM ---

class RagQueryInput(BaseModel):
    action: Literal["query_rag"] = "query_rag"
    query: str = Field(..., description="The specific question the user is asking about their documents.")

class SendEmailInput(BaseModel):
    action: Literal["send_email"] = "send_email"
    recipient: str = Field(..., description="The email address of the recipient.")
    subject: str = Field(..., description="The subject of the email.")
    body: str = Field(..., description="The main content/body of the email.")

class ScheduleMeetingInput(BaseModel):
    action: Literal["schedule_meeting"] = "schedule_meeting"
    # Add fields relevant for scheduling, e.g., participants, date, time, platform
    participants: List[str] = Field(..., description="List of participants for the meeting.")
    date_time: str = Field(..., description="Proposed date and time for the meeting, e.g., 'tomorrow at 3 PM'.")
    platform: Optional[str] = Field(None, description="Optional platform like Zoom, Teams, etc.")

class GeneralChatOutput(BaseModel):
    action: Literal["general_chat"] = "general_chat"
    response: str = Field(..., description="A general response to the user's message if no specific action/query is identified.")

class UnknownOutput(BaseModel):
    action: Literal["unknown"] = "unknown"
    reason: str = Field(..., description="Explanation why the intent could not be determined.")

# Union of all possible structured outputs
IntentOutput = Union[RagQueryInput, SendEmailInput, ScheduleMeetingInput, GeneralChatOutput, UnknownOutput]

# --- Updated ConversationHandler ---

class ConversationHandler:
    # Accept LLM, optionally pre-configure integrations
    def __init__(self, llm: BaseLLM):
        self.llm = llm
        # Integrations can be initialized here or lazily in handlers
        # TODO: Make integrations configurable/pluggable
        self.email_integration = EmailIntegration()
        # self.calendar_integration = CalendarIntegration() # etc.

    async def process_message(self, message: str, db: Session, user_id: str) -> Dict[str, Any]:
        """Process a natural language message, determine intent, extract entities, and execute."""

        # 1. Get conversation history
        history = crud_conversation.get_conversation_history(db, user_id=user_id, limit=5) # Get last 5 turns

        # 2. Use LLM to determine intent and extract entities, providing history
        try:
            structured_output: IntentOutput = await self._extract_intent_llm(message, history)
            print(f"LLM structured output: {structured_output}") # Log output
        except Exception as e:
            print(f"Error during LLM intent extraction: {e}")
            # Fallback or return error
            result = {"error": "Could not process request with LLM.", "details": str(e)}
            # Save error response to history as well?
            crud_conversation.create_conversation_entry(db, user_id=user_id, message=message, response_data=result)
            return result

        # 3. Execute the appropriate action based on the LLM output
        action = structured_output.action
        result = {}
        # Pass history to handlers if they need it
        if action == "query_rag":
            result = await self._handle_rag_query(structured_output.query, db, history)
        elif action == "send_email":
            result = await self._handle_send_email(structured_output, history)
        elif action == "schedule_meeting":
            result = await self._handle_schedule_meeting(structured_output, history)
        elif action == "general_chat":
            result = {"response": structured_output.response}
        elif action == "unknown":
            result = {"response": f"Sorry, I couldn't understand that. Reason: {structured_output.reason}"}
        else:
            print(f"Error: Unhandled action type: {action}")
            result = {"error": f"Internal error: Unhandled action type: {action}"}

        # 4. Save the current message and the final result to history
        try:
            crud_conversation.create_conversation_entry(db, user_id=user_id, message=message, response_data=result)
        except Exception as e:
            print(f"Error saving conversation history: {e}")
            # Don't let saving history break the response to the user
            # But maybe add the error to the response?
            result["history_error"] = f"Failed to save interaction: {e}"

        return result

    async def _extract_intent_llm(self, message: str, history: List[Dict[str, str]]) -> IntentOutput:
        """Use LLM to extract intent and entities based on predefined schemas, considering history."""
        
        history_str = "\n".join([f"{turn['role']}: {turn['content']}" for turn in history])
        if not history_str:
             history_str = "No previous conversation history."

        prompt = f"""
Consider the following conversation history:
<history>
{history_str}
</history>

Now, analyze the latest user message: "{message}"

Determine the primary intent and extract relevant entities based on the available actions, considering the context from the history.

Available actions and their required entities:
1.  **query_rag**: User is asking a question about their documents or knowledge base (e.g., "what did the report say about X?", "summarize the meeting notes").
    - **query**: The specific question being asked.
2.  **send_email**: User wants to send an email (e.g., "email John about the project update").
    - **recipient**: Email address or name of the recipient.
    - **subject**: Subject line of the email.
    - **body**: Main content of the email.
3.  **schedule_meeting**: User wants to schedule a meeting (e.g., "schedule a meeting with Jane tomorrow at 2 PM on Slack").
    - **participants**: List of people to invite.
    - **date_time**: Proposed date and time.
    - **platform**: (Optional) Platform like Zoom, Slack.
4.  **general_chat**: The user message is conversational, a greeting, small talk, or doesn't match other actions (e.g., "hello", "how are you?", "thanks"). Provide a suitable general response, considering the history.
5.  **unknown**: If the intent is unclear, ambiguous, or cannot be fulfilled. Provide a brief reason.

Determine the single most appropriate action for the *latest user message* and extract all necessary entities for that action.
Respond ONLY with a JSON object matching the structure for the chosen action (either query_rag, send_email, schedule_meeting, general_chat, or unknown).
Ensure the JSON is valid and complete according to the specified fields for the action.
For send_email, try to infer recipient, subject and body from the message and history. If crucial information is missing, ask for clarification using the 'unknown' action.
For query_rag, extract the core question from the latest message.
For general_chat, formulate a brief, appropriate response based on the latest message and history.

JSON Response:
"""
        # This part depends heavily on the specific LLM's capabilities for structured output.
        # Using OpenAI's function calling or Anthropic's tool use is ideal.
        # For a simpler approach (less reliable), we ask the LLM to generate JSON.

        # Example assuming LLM can generate JSON based on the prompt:
        llm_response = await self.llm.generate(prompt, max_tokens=500) # Adjust max_tokens
        response_text = llm_response.text.strip()
        print(f"Raw LLM response for intent: {response_text}")

        # Try to find JSON within potential markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text.split("```json", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
        response_text = response_text.strip()

        try:
            # Attempt to parse the LLM response as JSON
            output_data = json.loads(response_text)

            # Validate against our Pydantic models
            possible_types = [RagQueryInput, SendEmailInput, ScheduleMeetingInput, GeneralChatOutput, UnknownOutput]
            parsed_output = None
            validation_errors = []
            for p_type in possible_types:
                try:
                    # Check if the 'action' field matches before full parsing
                    if output_data.get("action") == p_type.model_fields["action"].default:
                        parsed_output = p_type.model_validate(output_data)
                        print(f"Successfully parsed as {p_type.__name__}")
                        break # Stop on first successful parse
                except Exception as val_err:
                    validation_errors.append(f"Failed to validate as {p_type.__name__}: {val_err}")
                    continue # Try next type

            if parsed_output:
                 return parsed_output
            else:
                 # If no type matched after parsing JSON
                 print(f"LLM JSON output did not match any known schema or failed validation: {output_data}")
                 print(f"Validation errors: {validation_errors}")
                 return UnknownOutput(reason=f"LLM output structure mismatch or validation failed. Errors: {validation_errors}")

        except json.JSONDecodeError:
            # Handle cases where the LLM didn't return valid JSON
            print(f"LLM did not return valid JSON: {response_text}")
            return UnknownOutput(reason=f"Could not parse LLM response as JSON: {response_text}")
        except Exception as e:
            # Handle Pydantic validation errors or other issues
            print(f"Error parsing/validating LLM output: {e}")
            return UnknownOutput(reason=f"Error processing LLM response: {e}")

    async def _handle_rag_query(self, query: str, db: Session, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle RAG queries by searching vector store and synthesizing answer with LLM, considering history."""
        print(f"Handling RAG query: {query}")
        try:
            # 1. Initialize embeddings and vector store
            if not settings.OPENAI_API_KEY:
                 print("Error: OPENAI_API_KEY not configured for RAG handler.")
                 return {"error": "OPENAI_API_KEY not configured"}
            # Consider making embeddings a class member if key doesn't change often
            embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
            vector_store = PostgreSQLVectorStore(db=db, embedding_function=embeddings)

            # 2. Search for relevant documents
            search_results = vector_store.similarity_search(query=query, k=3)
            print(f"Found {len(search_results)} relevant documents.")

            # 3. Construct prompt for LLM synthesis, including history
            if not search_results:
                context = "No relevant information found in the knowledge base."
            else:
                context = "\n\n".join([f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" for doc in search_results])
            
            history_str = "\n".join([f"{turn['role']}: {turn['content']}" for turn in history])
            if not history_str:
                 history_str = "No previous conversation history."

            synthesis_prompt = f"""
Conversation History:
<history>
{history_str}
</history>

Relevant Context from Knowledge Base:
<context>
{context}
</context>

Based *only* on the conversation history and the provided context from the knowledge base, answer the *latest user question*: "{query}"

If the context does not contain the necessary information, explicitly state that the answer cannot be found in the knowledge base based on the provided context.
Do not make up information or use external knowledge beyond the provided history and context.

Answer:"""
            print(f"Synthesizing answer for query: {query}")
            # 4. Generate response using LLM
            llm_response = await self.llm.generate(synthesis_prompt, max_tokens=1000) # Adjust tokens
            print(f"LLM synthesis response: {llm_response.text}")
            return {"response": llm_response.text}

        except Exception as e:
            print(f"Error during RAG query handling: {e}")
            return {"error": "Failed to answer question using knowledge base.", "details": str(e)}

    async def _handle_send_email(self, params: SendEmailInput, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Handle sending an email using the EmailIntegration."""
        print(f"Handling send email: To={params.recipient}, Subject={params.subject}")
        # History could be used here to confirm details if needed
        try:
            # Assuming EmailIntegration is already initialized in __init__
            # TODO: Add actual email sending logic configuration check
            print(f"Attempting to send email via integration... (Implementation Pending in EmailIntegration)")
            # result = await self.email_integration.send_email(
            #     to_email=params.recipient,
            #     subject=params.subject,
            #     body=params.body
            # )
            # Simulate success for now
            return {"response": f"OK. I will send an email to {params.recipient} with subject '{params.subject}'. (Actual sending pending)"}
        except Exception as e:
            print(f"Error sending email: {e}")
            return {"error": "Failed to send email.", "details": str(e)}

    async def _handle_schedule_meeting(self, params: ScheduleMeetingInput, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Placeholder for handling meeting scheduling."""
        print(f"Handling schedule meeting: Participants={params.participants}, DateTime={params.date_time}, Platform={params.platform}")
        # History could be used here
        # TODO: Implement actual calendar integration logic
        return {"response": f"OK. I'll schedule a meeting with {', '.join(params.participants)} for {params.date_time}. (Implementation Pending)"} 