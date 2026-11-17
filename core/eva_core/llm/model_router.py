import logging
import os
import sqlite3
import sys
from typing import Any, Dict, Optional, Tuple
import core.eva_core.database as db_module
from core.eva_core.llm.provider import LLMProvider, PlanningProvider
from core.eva_core.llm.ollama_provider import OllamaProvider
from core.eva_core.llm.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

class PrivacyMode:
    PRIVATE = "private"
    PUBLIC = "public"
    HYBRID = "hybrid"

class ModelRouter:
    """
    Intelligent Public / Private / Hybrid AI Model Router.
    Enforces privacy boundaries at the core architecture level:
    - PRIVATE: Only local Ollama model. External network LLM requests are blocked.
    - PUBLIC: Prefers Gemini for reasoning/planning, falls back to Ollama if unconfigured.
    - HYBRID: Routine operations run locally; complex tasks routed to Gemini only if
              the request does not touch private documents or sensitive context.
    """

    def __init__(
        self,
        ollama_provider: Optional[OllamaProvider] = None,
        gemini_provider: Optional[GeminiProvider] = None,
        default_mode: str = PrivacyMode.HYBRID,
    ):
        self._ollama = ollama_provider or OllamaProvider(
            model=os.environ.get("EVA_INTENT_MODEL", "llama3.2:3b")
        )
        self.gemini = gemini_provider or GeminiProvider()
        self._default_mode = default_mode

    @property
    def ollama(self):
        main_mod = sys.modules.get("core.eva_core.main")
        if main_mod and hasattr(main_mod, "llm_provider"):
            return main_mod.llm_provider
        return self._ollama

    def get_privacy_mode(self) -> str:
        """Fetch current privacy mode from SQLite system_config or fallback to env/default."""
        try:
            with sqlite3.connect(db_module.DB_PATH, timeout=2) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM system_config WHERE key = 'privacy_mode'")
                row = cursor.fetchone()
                if row and row[0]:
                    mode = row[0].lower().strip().replace('"', '')
                    if mode in {PrivacyMode.PRIVATE, PrivacyMode.PUBLIC, PrivacyMode.HYBRID}:
                        return mode
        except Exception:
            pass
        return os.environ.get("EVA_PRIVACY_MODE", self._default_mode).lower()

    def set_privacy_mode(self, mode: str) -> None:
        """Persist privacy mode in SQLite database."""
        mode = mode.lower().strip()
        if mode not in {PrivacyMode.PRIVATE, PrivacyMode.PUBLIC, PrivacyMode.HYBRID}:
            raise ValueError(f"Invalid privacy mode: {mode}. Allowed: private, public, hybrid")
        with sqlite3.connect(db_module.DB_PATH, timeout=5) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO system_config (key, value) VALUES ('privacy_mode', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (mode,),
            )
            conn.commit()
        logger.info("Privacy mode set to %s", mode)

    def route_provider(
        self,
        intent: Optional[str] = None,
        contains_private_data: bool = False,
        requires_complex_reasoning: bool = False,
    ) -> Tuple[LLMProvider, str, str]:
        """
        Determines the appropriate provider based on the active privacy mode,
        context sensitivity, and task complexity.
        Returns: (provider, provider_name, reason)
        """
        mode = self.get_privacy_mode()

        # 1. STRICT PRIVATE MODE: Never allow external requests
        if mode == PrivacyMode.PRIVATE:
            return (
                self.ollama,
                "ollama",
                "Private mode enforced. Local execution only.",
            )

        # 2. Strict Privacy Guard: If sensitive or private data is present, route locally
        if contains_private_data:
            return (
                self.ollama,
                "ollama",
                "Sensitive or private context detected; restricted to local model.",
            )

        # 3. PUBLIC MODE: Use Gemini if configured, otherwise fallback to local
        if mode == PrivacyMode.PUBLIC:
            if self.gemini.is_configured():
                return (
                    self.gemini,
                    "gemini",
                    "Public mode active. Routed to cloud Gemini engine.",
                )
            else:
                return (
                    self.ollama,
                    "ollama",
                    "Public mode requested, but Gemini API key not configured. Falling back to Ollama.",
                )

        # 4. HYBRID MODE: Selective routing based on task nature
        # Complex tasks, code generation, and multi-step reasoning benefit from Gemini
        is_complex = (
            requires_complex_reasoning
            or intent in {"complex_task", "document_operation", "code_generation"}
        )

        if is_complex and self.gemini.is_configured():
            return (
                self.gemini,
                "gemini",
                "Hybrid mode: complex task routed to Gemini for advanced reasoning.",
            )

        # Routine tasks, desktop commands, file operations stay local
        return (
            self.ollama,
            "ollama",
            "Hybrid mode: standard task routed to local Ollama model.",
        )

    def get_planning_provider(self, contains_private_data: bool = False) -> Tuple[PlanningProvider, str]:
        """Returns planning provider according to privacy settings."""
        provider, name, _ = self.route_provider(
            intent="complex_task",
            contains_private_data=contains_private_data,
            requires_complex_reasoning=True,
        )
        return provider, name

    async def health(self) -> Dict[str, Any]:
        """Return health of both Ollama and Gemini providers along with active mode."""
        gemini_health = await self.gemini.health_check()
        ollama_available = False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.ollama.base_url}/api/tags")
                ollama_available = res.status_code == 200
        except Exception:
            pass

        return {
            "mode": self.get_privacy_mode(),
            "ollama": {
                "available": ollama_available,
                "model": self.ollama.model,
                "base_url": self.ollama.base_url,
            },
            "gemini": gemini_health,
        }
