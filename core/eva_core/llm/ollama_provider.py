import httpx
import json
import logging
from typing import Dict, Any
from .provider import LLMProvider, PlanningProvider

class OllamaProvider(LLMProvider, PlanningProvider):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def generate_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "format": "json",
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "{}")
                return json.loads(result_text)
        except httpx.RequestError as e:
            logging.error(f"Ollama connection error: {e}")
            raise RuntimeError(f"Ollama provider unavailable: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"Ollama returned invalid JSON: {e}")
            raise RuntimeError(f"Invalid JSON response from model: {e}")

    async def generate_plan(self, prompt: str, system: str = "") -> Dict[str, Any]:
        """Uses the exact same infrastructure for planning."""
        return await self.generate_json(prompt, system)
