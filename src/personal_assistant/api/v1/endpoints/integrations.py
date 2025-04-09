from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from personal_assistant.integrations.email import EmailIntegration
from personal_assistant.integrations.base import BaseIntegration
from personal_assistant.core.security import get_current_user

router = APIRouter()

class IntegrationConfig(BaseModel):
    type: str
    config: Dict[str, Any]

class IntegrationResponse(BaseModel):
    status: str
    details: Dict[str, Any]

# Store active integrations
active_integrations: Dict[str, BaseIntegration] = {}

@router.post("/connect", response_model=IntegrationResponse)
async def connect_integration(
    integration_config: IntegrationConfig,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Connect a new integration"""
    try:
        if integration_config.type == "email":
            integration = EmailIntegration(integration_config.config)
        else:
            raise HTTPException(status_code=400, detail="Unsupported integration type")
        
        await integration.initialize()
        connected = await integration.connect()
        
        if connected:
            active_integrations[integration_config.type] = integration
            return IntegrationResponse(
                status="connected",
                details=await integration.get_status()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to integration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=Dict[str, IntegrationResponse])
async def get_integrations_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get status of all connected integrations"""
    status = {}
    for integration_type, integration in active_integrations.items():
        status[integration_type] = IntegrationResponse(
            status="connected" if integration.is_connected else "disconnected",
            details=await integration.get_status()
        )
    return status

@router.post("/{integration_type}/send")
async def send_message(
    integration_type: str,
    message: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Send a message through an integration"""
    if integration_type not in active_integrations:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration = active_integrations[integration_type]
    success = await integration.send_message(message)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")
    
    return {"status": "success"}

@router.get("/{integration_type}/messages")
async def get_messages(
    integration_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get messages from an integration"""
    if integration_type not in active_integrations:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration = active_integrations[integration_type]
    messages = await integration.get_messages()
    
    return {"messages": messages} 