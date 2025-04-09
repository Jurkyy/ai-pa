from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseIntegration(ABC):
    """Base class for all integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the integration with necessary setup"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the service"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service"""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the integration"""
        pass

    @abstractmethod
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle incoming events from the service"""
        pass

    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> bool:
        """Send a message through the integration"""
        pass

    @abstractmethod
    async def get_messages(self, **kwargs) -> List[Dict[str, Any]]:
        """Retrieve messages from the integration"""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the integration is connected"""
        return self.initialized 