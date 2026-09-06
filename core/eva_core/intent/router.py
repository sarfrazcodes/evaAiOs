from core.eva_core.models_intent import IntentModel, RouteResult
import logging

class Router:
    def route(self, intent_model: IntentModel) -> RouteResult:
        """Determines the correct subsystem route based on the intent."""
        # Configurable confidence threshold
        if intent_model.confidence < 0.6:
            logging.warning("Low confidence intent, routing to clarification.")
            return RouteResult(route="clarification", intent=intent_model.intent, confidence=intent_model.confidence)

        intent_to_route = {
            "conversation": "conversation",
            "information_request": "information",
            "system_command": "system",
            "file_operation": "file",
            "application_operation": "application",
            "browser_operation": "browser",
            "document_operation": "document",
            "complex_task": "planner",
            "unsupported": "unsupported",
            "ambiguous": "clarification"
        }

        # Default route is 'unknown' if not explicitly handled
        route_name = intent_to_route.get(intent_model.intent, "unknown")
        return RouteResult(route=route_name, intent=intent_model.intent, confidence=intent_model.confidence)
