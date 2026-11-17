import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Dict, Optional
import httpx
from .provider import LLMProvider, PlanningProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider, PlanningProvider):
    """
    Direct REST provider for Google Gemini API using httpx.
    Supports JSON output, text streaming, task planning, and health checks.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        timeout: float = 60.0,
    ):
        self._explicit_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def api_key(self) -> str:
        """Fetch API key from explicit init, environment variable, or return empty string."""
        if self._explicit_key and self._explicit_key.strip():
            return self._explicit_key.strip()
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key and env_key.strip():
            return env_key.strip()
        # Fallback to sqlite database system_config if available
        try:
            import sqlite3
            import core.eva_core.database as db_module
            with sqlite3.connect(db_module.DB_PATH, timeout=2) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM system_config WHERE key = 'gemini_api_key'")
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0].strip()
        except Exception:
            pass
        return ""

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def health_check(self) -> Dict[str, Any]:
        """Check if Gemini API is configured and reachable."""
        key = self.api_key
        if not key:
            return {
                "available": False,
                "configured": False,
                "model": self.model,
                "error": "GEMINI_API_KEY is not configured.",
            }
        try:
            url = f"{self.base_url}/models/{self.model}?key={key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return {
                        "available": True,
                        "configured": True,
                        "model": self.model,
                        "error": None,
                    }
                else:
                    err_msg = res.json().get("error", {}).get("message", f"HTTP {res.status_code}")
                    return {
                        "available": False,
                        "configured": True,
                        "model": self.model,
                        "error": err_msg,
                    }
        except Exception as exc:
            return {
                "available": False,
                "configured": True,
                "model": self.model,
                "error": str(exc),
            }

    async def generate_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        key = self.api_key
        if not key:
            raise RuntimeError("Gemini API key is not configured. Set GEMINI_API_KEY or configure in Settings.")

        url = f"{self.base_url}/models/{self.model}:generateContent?key={key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    err = res.json().get("error", {}).get("message", f"HTTP {res.status_code}")
                    raise RuntimeError(f"Gemini API error: {err}")
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates.")
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                # Strip markdown code fences if model enclosed JSON
                clean = re.sub(r"^```(?:json)?\s*", "", text.strip())
                clean = re.sub(r"\s*```$", "", clean)
                return json.loads(clean)
        except json.JSONDecodeError as exc:
            logger.error("Gemini invalid JSON response: %s", exc)
            raise RuntimeError(f"Invalid JSON response from Gemini: {exc}")
        except httpx.HTTPError as exc:
            logger.error("Gemini network error: %s", exc)
            raise RuntimeError(f"Gemini connection error: {exc}")

    async def generate_plan(self, prompt: str, system: str = "") -> Dict[str, Any]:
        return await self.generate_json(prompt, system)

    async def stream_text(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        key = self.api_key
        if not key:
            raise RuntimeError("Gemini API key is not configured.")

        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f"Gemini stream error: HTTP {response.status_code}")
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            candidates = chunk_data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    txt = part.get("text", "")
                                    if txt:
                                        yield txt
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as exc:
            logger.error("Gemini stream connection error: %s", exc)
            raise RuntimeError(f"Gemini streaming failed: {exc}")
