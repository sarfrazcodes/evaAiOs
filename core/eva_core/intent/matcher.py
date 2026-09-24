import re
import difflib
from typing import Optional, Dict, Any, Tuple
from core.eva_core.models_intent import IntentModel
from .normalizer import normalize_input
from .lexicon import INTENT_LEXICON

def _get_fuzzy_match(word: str, possibilities: list[str], cutoff=0.75) -> Optional[str]:
    matches = difflib.get_close_matches(word, possibilities, n=1, cutoff=cutoff)
    if matches:
        if abs(len(word) - len(matches[0])) <= 1:
            return matches[0]
    return None

class IntentMatcher:
    def match(self, original_text: str) -> Optional[IntentModel]:
        text = normalize_input(original_text)
        if not text:
            return None

        # Check exact matches across all intents
        for intent_cat, lexicon in INTENT_LEXICON.items():
            if "exact" in lexicon:
                if text in lexicon["exact"]:
                    return IntentModel(intent=intent_cat, confidence=1.0, reason=f"Exact match for {intent_cat}", parameters={})

        # Fuzzy exact match
        all_exacts = []
        exact_to_intent = {}
        for intent_cat, lexicon in INTENT_LEXICON.items():
            if "exact" in lexicon:
                for phrase in lexicon["exact"]:
                    all_exacts.append(phrase)
                    exact_to_intent[phrase] = intent_cat
        
        fuzzy_exact = _get_fuzzy_match(text, all_exacts, cutoff=0.85)
        if fuzzy_exact:
            # Check for multiple plausible intents? difflib only returns best match.
            # But we should be conservative.
            return IntentModel(intent=exact_to_intent[fuzzy_exact], confidence=0.9, reason=f"Fuzzy exact match for {fuzzy_exact}", parameters={})
            
        # Pattern matching for applications
        app_lex = INTENT_LEXICON.get("application_operation", {})
        prefixes = app_lex.get("prefixes", [])
        
        # Try finding prefix + app name
        for prefix in prefixes:
            if text.startswith(prefix + " "):
                remainder = text[len(prefix):].strip()
                # Ensure the remainder isn't a huge sentence
                if len(remainder.split()) <= 3:
                    # Fuzzy match the app name against known apps? The user said "use conservative fuzzy match"
                    # But we can also just accept the remainder if it's short, like in previous version,
                    # OR we can try to fuzzy match known apps.
                    known_apps = app_lex.get("apps", [])
                    fuzzy_app = _get_fuzzy_match(remainder, known_apps, cutoff=0.8)
                    app_name = fuzzy_app if fuzzy_app else remainder
                    
                    return IntentModel(
                        intent="application_operation",
                        confidence=1.0 if fuzzy_app else 0.9,
                        reason="Pattern match for application",
                        parameters={"application": app_name}
                    )
        
        # We can also handle fuzzy matching for prefixes
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            first_word = parts[0]
            rest = parts[1]
            
            # Application fuzzy prefix (e.g. "opne")
            fuzzy_prefix = _get_fuzzy_match(first_word, ["open", "launch", "start", "run"], cutoff=0.75)
            if fuzzy_prefix and len(rest.split()) <= 3:
                known_apps = app_lex.get("apps", [])
                fuzzy_app = _get_fuzzy_match(rest, known_apps, cutoff=0.8)
                app_name = fuzzy_app if fuzzy_app else rest
                return IntentModel(
                    intent="application_operation",
                    confidence=0.85,
                    reason="Fuzzy pattern match for application",
                    parameters={"application": app_name}
                )

            # Browser fuzzy prefix
            fuzzy_browser = _get_fuzzy_match(first_word, ["search", "google", "find"], cutoff=0.8)
            if fuzzy_browser:
                return IntentModel(
                    intent="browser_operation",
                    confidence=0.85,
                    reason="Fuzzy pattern match for browser",
                    parameters={"query": rest}
                )

        # Conversational fallback heuristic
        # If the input is long and doesn't start with action words, it's highly likely to be a conversation.
        action_verbs = {
            "open", "launch", "start", "run", "create", "make", "new", "list", "show", "read", "view",
            "search", "google", "find", "browse", "take", "shutdown", "restart", "lock", "check", 
            "turn", "enable", "research", "tell", "please", "can", "could", "write"
        }
        
        words = text.split()
        if len(words) >= 4:
            if words[0] not in action_verbs:
                return IntentModel(
                    intent="conversation",
                    confidence=0.85,
                    reason="Conversational heuristic fallback",
                    parameters={}
                )

        return None
