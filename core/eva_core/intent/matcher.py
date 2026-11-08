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
                    parameters = {}
                    if intent_cat == "desktop_operation":
                        parameters = {"request": text}
                    elif intent_cat == "desktop_control":
                        operation = "read_volume" if text in {"read volume", "what is the volume"} else "mute" if text in {"mute audio", "mute sound"} else "unmute"
                        parameters = {"operation": operation}
                    return IntentModel(intent=intent_cat, confidence=1.0, reason=f"Exact match for {intent_cat}", parameters=parameters)

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

        volume_match = re.fullmatch(r"(?:set|change|turn) volume to (\d+(?:\.\d+)?)", text)
        if volume_match:
            return IntentModel(
                intent="desktop_control",
                confidence=1.0,
                reason="Deterministic volume control",
                parameters={"operation": "set_volume", "value": float(volume_match.group(1))},
            )

        file_create_match = re.fullmatch(
            r"(?:create|make|new) (?:a )?(file|folder|directory)(?: (?:called|named) (.+))?",
            text,
        )
        if file_create_match and file_create_match.group(2):
            kind, path = file_create_match.groups()
            return IntentModel(
                intent="file_operation",
                confidence=1.0,
                reason="Deterministic file operation",
                parameters={
                    "operation": "create_file" if kind == "file" else "create_directory",
                    "path": path.strip(),
                },
            )

        file_read_match = re.fullmatch(r"(?:read|view|open) (?:the )?file (?:called |named )?(.+)", text)
        if file_read_match:
            return IntentModel(
                intent="file_operation",
                confidence=1.0,
                reason="Deterministic file operation",
                parameters={"operation": "read_file", "path": file_read_match.group(1).strip()},
            )

        if text in {"close it", "quit it", "exit it", "close that", "close the same application"}:
            return IntentModel(
                intent="application_operation",
                confidence=1.0,
                reason="Contextual application lifecycle command",
                parameters={"application": "__context__", "operation": "close"},
            )

        running_match = re.fullmatch(r"(?:is|check if|check whether) (chrome|google chrome|firefox|brave|brave browser|vscode|vs code|visual studio code|file manager) running", text)
        if running_match:
            return IntentModel(
                intent="application_operation",
                confidence=1.0,
                reason="Deterministic application state query",
                parameters={"application": running_match.group(1).strip(), "operation": "check_running"},
            )

        if re.fullmatch(r"(?:open|launch|start) (?:notepad|a text editor|the text editor|whatever text editor is available|notepad or whatever text editor is available)", text):
            return IntentModel(
                intent="application_operation",
                confidence=1.0,
                reason="Deterministic editor discovery request",
                parameters={"application": "text editor", "operation": "open"},
            )

        if text.startswith(("write a short paragraph", "write a paragraph", "write about")):
            return IntentModel(
                intent="editor_operation",
                confidence=1.0,
                reason="Deterministic editor writing request",
                parameters={"operation": "write_text", "request": original_text},
            )

        if (
            re.search(r"\b(open|launch|start)\s+(chrome|google chrome|firefox|brave|vscode|vs code|visual studio code)\b.*\b(search|google|look up|find)\b", text)
            or re.search(r"\b(minimize|hide)\b.*\b(open|launch|start)\b.*\b(play|youtube)\b", text)
            or re.search(r"\b(open|launch|start)\s+(?:chrome|google chrome|firefox|brave|vscode|vs code|visual studio code)\b.*\b(play|youtube)\b", text)
            or re.search(r"\b(search|google|look up|find)\b.+\bthen\b.+\b(search|google|look up|find)\b", text)
            or re.search(r"\b(open|launch|start)\s+(?:chrome|google chrome|firefox|brave|vscode|vs code|visual studio code)\b\s+and\s+(?:open\s+)?(?:chrome|google chrome|firefox|brave|vscode|vs code|visual studio code)\b", text)
        ):
            return IntentModel(
                intent="complex_task",
                confidence=1.0,
                reason="Deterministic multi-step desktop request",
                parameters={"control_request": text},
            )
            
        # Match browser searches before application actions so "search in Chrome"
        # remains a browser operation rather than an application launch.
        search_match = re.fullmatch(r"(?:search|google|look up|find)(?: for)? (.+?)(?: in| on) (chrome|google chrome|firefox|brave|brave browser)", text)
        if search_match:
            return IntentModel(
                intent="browser_operation",
                confidence=1.0,
                reason="Deterministic browser search",
                parameters={"query": search_match.group(1).strip(), "application": search_match.group(2).strip()},
            )
        search_match = re.fullmatch(r"search (?:google|the web) for (.+)", text)
        if search_match:
            return IntentModel(
                intent="browser_operation",
                confidence=1.0,
                reason="Deterministic browser search",
                parameters={"query": search_match.group(1).strip(), "new_tab": False},
            )
        youtube_match = re.fullmatch(r"(?:play|search youtube for|search for) (.+?)(?: on youtube)?", text)
        if youtube_match and ("youtube" in text or text.startswith("play ")):
            return IntentModel(
                intent="browser_operation",
                confidence=1.0,
                reason="Deterministic YouTube search",
                parameters={"query": youtube_match.group(1).strip(), "search_provider": "youtube", "application": "firefox" if "firefox" in text else None},
            )
        search_match = re.fullmatch(r"(?:now\s+)?(?:in\s+)?(?:a\s+)?(?:new\s+tab\s+)?(?:search|google|look up|find)(?: for)? (.+)", text)
        if search_match:
            prefix = text[:search_match.start(1)].strip()
            return IntentModel(
                intent="browser_operation",
                confidence=1.0,
                reason="Deterministic browser search",
                parameters={"query": search_match.group(1).strip(), "new_tab": "new tab" in prefix},
            )
        search_match = re.fullmatch(r"(?:search|google|look up|find)(?: for)? (.+)", text)
        if search_match:
            return IntentModel(
                intent="browser_operation",
                confidence=1.0,
                reason="Deterministic browser search",
                parameters={"query": search_match.group(1).strip()},
            )

        # Match an approved application anywhere in a short action request,
        # allowing natural fillers such as "hey could you" and "for me".
        app_lex = INTENT_LEXICON.get("application_operation", {})
        action_words = {"open", "opened", "launch", "launched", "start", "started", "run", "running", "close", "closed", "quit", "exit", "terminate", "focus", "switch"}
        if any(word in action_words for word in text.split()):
            known_apps = sorted(app_lex.get("apps", []), key=len, reverse=True)
            for app_name in known_apps:
                if re.search(rf"\b{re.escape(app_name)}\b", text):
                    if app_name == "notepad":
                        app_name = "text editor"
                    operation = "open"
                    if any(word in text.split() for word in {"close", "closed", "quit", "exit", "terminate"}):
                        operation = "close"
                    elif any(word in text.split() for word in {"focus", "switch"}):
                        operation = "focus"
                    return IntentModel(
                        intent="application_operation",
                        confidence=1.0,
                        reason="Natural-language application action",
                        parameters={
                            "application": app_name,
                            "operation": operation,
                            "new_window": "new window" in text,
                        },
                    )

        prefixes = app_lex.get("prefixes", [])
        
        # We can also handle fuzzy matching for prefixes
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            first_word = parts[0]
            rest = parts[1]
            
            # Application fuzzy prefix (e.g. "opne")
            fuzzy_prefix = _get_fuzzy_match(first_word, ["open", "launch", "start", "run", "close", "quit", "exit", "focus"], cutoff=0.75)
            if fuzzy_prefix and len(rest.split()) <= 3:
                known_apps = app_lex.get("apps", [])
                fuzzy_app = _get_fuzzy_match(rest, known_apps, cutoff=0.8)
                app_name = fuzzy_app if fuzzy_app else rest
                return IntentModel(
                    intent="application_operation",
                    confidence=0.85,
                    reason="Fuzzy pattern match for application",
                    parameters={"application": app_name, "operation": "close" if fuzzy_prefix in {"close", "quit", "exit"} else "focus" if fuzzy_prefix == "focus" else "open"}
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

        # Common informational questions should stream immediately instead of
        # requiring a second local LLM call just to choose the information route.
        informational_prefixes = (
            "tell me", "tell all", "explain", "what is", "what are",
            "who is", "why is", "why are", "how do i", "how can i",
        )
        if text.startswith(informational_prefixes):
            return IntentModel(
                intent="information_request",
                confidence=0.9,
                reason="Informational question heuristic",
                parameters={},
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
