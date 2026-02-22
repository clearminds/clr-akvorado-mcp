"""Middleware for friendlier tool validation errors."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware


class ToolValidationMiddleware(Middleware):
    """Catch Pydantic validation errors and return clear, actionable messages."""

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        try:
            return await call_next(context)
        except ValidationError as exc:
            tool_name = context.message.name
            provided = context.message.arguments or {}

            missing: list[str] = []
            unexpected: list[str] = []
            other: list[str] = []

            for err in exc.errors():
                field = str(err["loc"][0]) if err["loc"] else "?"
                err_type = err["type"]
                if err_type == "missing" or err_type == "missing_argument":
                    missing.append(field)
                elif err_type in ("unexpected_keyword_argument", "extra_forbidden"):
                    unexpected.append(field)
                else:
                    other.append(f"  {field}: {err['msg']}")

            parts = [f"Wrong arguments for '{tool_name}'."]
            if missing:
                parts.append(f"Required: {', '.join(missing)}")
            if unexpected:
                parts.append(f"Unexpected: {', '.join(unexpected)}")
            if missing and unexpected and len(missing) == 1 and len(unexpected) == 1:
                parts.append(
                    f"Hint: use '{missing[0]}' instead of '{unexpected[0]}'."
                )
            if other:
                parts.extend(other)
            parts.append(f"You provided: {sorted(provided.keys())}")

            raise ToolError("\n".join(parts)) from exc
