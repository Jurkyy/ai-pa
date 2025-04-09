from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
from pydantic import BaseModel

class LLMResponse(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass


class ClaudeLLM(BaseLLM):
    def __init__(self, model: str = "claude-3.5-haiku-latest"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 1000),
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return LLMResponse(
            text=response.content[0].text,
            metadata={
                "model": self.model,
                "usage": response.usage.dict() if hasattr(response, "usage") else {}
            }
        )

class OpenAILLM(BaseLLM):
    def __init__(self, model: str = "gpt-4"):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return LLMResponse(
            text=response.choices[0].message.content,
            metadata={
                "model": self.model,
                "usage": response.usage.dict() if hasattr(response, "usage") else {}
            }
        )

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [embedding.embedding for embedding in response.data]

def get_llm(provider: str = "claude") -> BaseLLM:
    """Factory function to get the appropriate LLM implementation"""
    if provider.lower() == "claude":
        return ClaudeLLM()
    elif provider.lower() == "openai":
        return OpenAILLM()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}") 