import logging
import re
from typing import Optional
from core.eva_core.models_intent import IntentModel
from core.eva_core.llm.provider import LLMProvider
from .matcher import IntentMatcher

INTENT_CATEGORIES = [
    "conversation",
    "information_request",
    "system_command",
    "file_operation",
    "application_operation",
    "browser_operation",
    "document_operation",
    "complex_task",
    "unsupported",
    "ambiguous"
]

class IntentEngine:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.matcher = IntentMatcher()

    async def determine_intent(self, user_content: str, context_str: Optional[str] = None) -> IntentModel:
        """Determines the intent of a user's request. Uses fast path first, falls back to LLM."""
        
        # 1. Fast Path
        fast_intent = self._evaluate_fast_path(user_content)
        if fast_intent:
            logging.info(f"Fast path matched intent: {fast_intent.intent}")
            return fast_intent

        # 2. LLM Fallback
        logging.info("Fast path missed, falling back to LLM Intent Provider...")
        
        llm_input = context_str if context_str else f"User request: {user_content}"
        
        try:
            return await self._evaluate_llm(llm_input)
        except Exception as e:
            logging.error(f"LLM Intent Engine failed: {e}")
            return IntentModel(intent="ambiguous", confidence=0.0, reason=f"Engine failure: {str(e)}")

    def _evaluate_fast_path(self, content: str) -> Optional[IntentModel]:
        return self.matcher.match(content)

    async def _evaluate_llm(self, content: str) -> IntentModel:
        system_prompt = f"""You are the intent classification engine for EVA AI OS.
Your ONLY job is to classify the user's intent into exactly one of the following categories: {INTENT_CATEGORIES}.

Definitions to distinguish:
information_request:
A request primarily asking for information, an answer, or generating text/code, without requiring a multi-step computer task on the user's machine.
Examples: "What are AI agents?", "Tell me about Linux.", "Write a python script for binary search.", "Give me code to break wifi.", "Tell me how to open Chrome.", "Explain how to use the browser."

complex_task:
A request requiring multiple operations, planning, or coordinated actions.
Examples: "Research AI agents and create a Word report.", "Open Chrome, search for AI operating systems, summarize the results, and save them to a document."

browser_operation:
A simple request to search the web or open a browser, without subsequent analysis or document creation. (Do NOT use this for requests asking FOR INFORMATION about a browser).
Examples: "Search the web for AI agents.", "Google python tutorials."

application_operation:
A request to open an application. (Do NOT use this for requests asking to write code, or asking FOR INFORMATION about an application).
Examples: "Open Chrome", "Launch VSCode".

file_operation:
A request to create, list, or manage files and directories. (Do NOT use this for requests asking for code generation).
Examples: "Create a folder", "List my files".

document_operation:
A request to create or manage documents specifically (e.g. word, spreadsheet).
Examples: "Create a Word document."

system_command:
A system level command like shutdown, or checking CPU usage.
Examples: "Check CPU usage", "Shutdown computer".

Return a JSON object with the following schema:
{{
    "intent": "category_name",
    "confidence": 0.0_to_1.0,
    "reason": "brief explanation",
    "parameters": {{}}
}}

Extract relevant variables into the 'parameters' object (e.g. filename, application name).
Do NOT include any extra text. Return strictly JSON.
"""
        result = await self.llm.generate_json(prompt=f"User request: {content}", system=system_prompt)
        
        intent_val = result.get("intent", "ambiguous")
        if intent_val not in INTENT_CATEGORIES:
            intent_val = "ambiguous"
            
        return IntentModel(
            intent=intent_val,
            confidence=float(result.get("confidence", 0.0)),
            reason=result.get("reason"),
            parameters=result.get("parameters", {})
        )
