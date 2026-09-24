from enum import Enum
from typing import Dict, Any

class PermissionDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    DENY = "deny"

class PermissionHook:
    def check_permission(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionDecision:
        """
        Stub for the future Permission System.
        In Phase 2D, safe test operations default to ALLOW.
        """
        # Baseline guard against dangerous patterns even in mock inputs
        for val in arguments.values():
            if isinstance(val, str):
                val_lower = val.lower()
                if "sudo " in val_lower or "rm -rf" in val_lower:
                    return PermissionDecision.DENY
        
        return PermissionDecision.ALLOW
