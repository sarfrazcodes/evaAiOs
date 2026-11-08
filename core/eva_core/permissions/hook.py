from enum import Enum
from typing import Dict, Any
import hashlib
import json
import secrets
import time

class PermissionDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    DENY = "deny"


class RiskClass(str, Enum):
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    CONFIRM_REQUIRED = "confirm_required"
    BLOCKED = "blocked"

class PermissionHook:
    CONFIRMATION_TTL_SECONDS = 60

    def __init__(self):
        self._confirmations: Dict[str, tuple[float, str]] = {}
        self._audit_log = []

    def risk_class(self, tool_name: str, arguments: Dict[str, Any]) -> RiskClass:
        operation = arguments.get("operation")
        if tool_name not in {"application_tool", "desktop_tool", "echo", "calculator", "file_tool"}:
            return RiskClass.BLOCKED
        if tool_name == "application_tool" and operation not in {"open", "focus", "check", "check_running", "close", "search", "write_text", "minimize", "restore", "list_windows", "youtube_search"}:
            return RiskClass.BLOCKED
        if tool_name == "desktop_tool" and operation not in {"open_directory", "read_volume", "set_volume", "mute", "unmute"}:
            return RiskClass.BLOCKED
        if tool_name == "file_tool" and operation not in {"read_file", "list_directory", "create_file", "create_directory"}:
            return RiskClass.BLOCKED
        if tool_name == "file_tool" and operation in {"create_file", "create_directory"}:
            return RiskClass.CONFIRM_REQUIRED
        if tool_name == "application_tool" and operation == "close":
            return RiskClass.CONFIRM_REQUIRED
        if tool_name == "application_tool" and operation == "write_text":
            return RiskClass.CONFIRM_REQUIRED
        if tool_name == "desktop_tool" and operation in {"set_volume", "mute", "unmute"}:
            return RiskClass.CONFIRM_REQUIRED
        return RiskClass.READ_ONLY if operation in {"read_file", "list_directory", "read_volume", "check", "check_running"} else RiskClass.LOW_RISK

    @staticmethod
    def _fingerprint(tool_name: str, arguments: Dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool_name, "arguments": arguments}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def request_confirmation(self, tool_name: str, arguments: Dict[str, Any]) -> str | None:
        if self.risk_class(tool_name, arguments) != RiskClass.CONFIRM_REQUIRED:
            return None
        token = secrets.token_urlsafe(24)
        self._confirmations[token] = (time.monotonic() + self.CONFIRMATION_TTL_SECONDS, self._fingerprint(tool_name, arguments))
        return token

    def _record(self, tool_name: str, arguments: Dict[str, Any], decision: PermissionDecision):
        self._audit_log.append({"tool": tool_name, "operation": arguments.get("operation"), "decision": decision.value, "timestamp": time.time()})
        del self._audit_log[:-200]

    def audit_log(self):
        return list(self._audit_log)

    def check_permission(self, tool_name: str, arguments: Dict[str, Any], confirmation_token: str | None = None) -> PermissionDecision:
        risk = self.risk_class(tool_name, arguments)
        for val in arguments.values():
            if isinstance(val, str):
                val_lower = val.lower()
                if any(pattern in val_lower for pattern in ("sudo ", "rm -rf", "shutdown", "reboot", "poweroff", ";", "&&", "|")):
                    self._record(tool_name, arguments, PermissionDecision.DENY)
                    return PermissionDecision.DENY
        if risk == RiskClass.BLOCKED:
            decision = PermissionDecision.DENY
        elif risk == RiskClass.CONFIRM_REQUIRED:
            confirmation = self._confirmations.pop(confirmation_token, None) if confirmation_token else None
            valid = confirmation and confirmation[0] > time.monotonic() and confirmation[1] == self._fingerprint(tool_name, arguments)
            decision = PermissionDecision.ALLOW if valid else PermissionDecision.REQUIRE_CONFIRMATION
        else:
            decision = PermissionDecision.ALLOW
        self._record(tool_name, arguments, decision)
        return decision

    def check_approved_permission(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionDecision:
        """Revalidate an already server-bound approval without trusting its caller."""
        risk = self.risk_class(tool_name, arguments)
        if risk in {RiskClass.BLOCKED, RiskClass.CONFIRM_REQUIRED}:
            for value in arguments.values():
                if isinstance(value, str) and any(pattern in value.lower() for pattern in ("sudo ", "rm -rf", "shutdown", "reboot", "poweroff", ";", "&&", "|")):
                    self._record(tool_name, arguments, PermissionDecision.DENY)
                    return PermissionDecision.DENY
            if risk == RiskClass.BLOCKED:
                self._record(tool_name, arguments, PermissionDecision.DENY)
                return PermissionDecision.DENY
        self._record(tool_name, arguments, PermissionDecision.ALLOW)
        return PermissionDecision.ALLOW
