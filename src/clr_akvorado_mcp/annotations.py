"""Tool annotation decorators.

Wraps ``mcp.tool(annotations=...)`` to give every tool an explicit
read / write / destructive classification. MCP clients use these hints
to surface the right UX (auto-approve reads, gate destructive writes).

Three buckets:
- ``@read_tool``         -> readOnlyHint=True,  destructiveHint=False
- ``@write_tool``        -> readOnlyHint=False, destructiveHint=False
- ``@destructive_tool``  -> readOnlyHint=False, destructiveHint=True
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from clr_akvorado_mcp.server import mcp

_READ = {"readOnlyHint": True, "destructiveHint": False}
_WRITE = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


def read_tool(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register ``fn`` as a read-only MCP tool."""
    return mcp.tool(annotations=_READ)(fn)


def write_tool(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register ``fn`` as a write MCP tool (mutating but reversible)."""
    return mcp.tool(annotations=_WRITE)(fn)


def destructive_tool(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register ``fn`` as a destructive MCP tool (delete/purge/force/wipe)."""
    return mcp.tool(annotations=_DESTRUCTIVE)(fn)
