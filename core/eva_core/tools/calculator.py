from typing import Dict, Any
from core.eva_core.tools.base import BaseTool
from core.eva_core.protocol import ToolResult

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Performs simple arithmetic operations (add, subtract, multiply, divide)."

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            op = arguments.get("operation")
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            
            if op == "add":
                res = a + b
            elif op == "subtract":
                res = a - b
            elif op == "multiply":
                res = a * b
            elif op == "divide":
                if b == 0:
                    return ToolResult(success=False, tool_name=self.name, message="Division by zero.", error="MathError")
                res = a / b
            else:
                return ToolResult(success=False, tool_name=self.name, message="Invalid operation.", error="InvalidInput")
                
            return ToolResult(success=True, tool_name=self.name, message="Calculation successful.", data={"result": res})
        except Exception as e:
            return ToolResult(success=False, tool_name=self.name, message="Error executing calculator.", error=str(e))
