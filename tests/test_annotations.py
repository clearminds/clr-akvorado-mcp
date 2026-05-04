"""Verify every registered tool has explicit read/write/destructive annotations."""

from __future__ import annotations

import asyncio

from clr_akvorado_mcp.server import mcp


def _list_tools() -> list:
    """Return all registered tools across FastMCP 2.x and 3.x.

    FastMCP 2.x exposes ``mcp.get_tools()`` (returning a ``dict[str, Tool]``);
    FastMCP 3.x replaced it with ``mcp.list_tools()`` (returning a ``list[Tool]``).
    The two APIs are mutually exclusive — this helper picks the one that exists.
    """
    if hasattr(mcp, "get_tools"):
        result = asyncio.run(mcp.get_tools())
        return list(result.values())
    return asyncio.run(mcp.list_tools())


def test_every_tool_has_annotations() -> None:
    """No tool may be registered without read/destructive annotations."""
    tools = _list_tools()
    assert tools, "No tools registered — did annotations.py fail to import?"
    missing: list[str] = []
    for t in tools:
        ann = t.annotations
        if ann is None or ann.readOnlyHint is None or ann.destructiveHint is None:
            missing.append(t.name)
    assert not missing, (
        f"Tools missing readOnlyHint/destructiveHint: {missing}. "
        "Use @read_tool / @write_tool / @destructive_tool from "
        "clr_akvorado_mcp.annotations instead of @mcp.tool."
    )


def test_at_least_one_read_tool() -> None:
    """Every server should have at least one read tool — sanity check."""
    tools = _list_tools()
    reads = [t.name for t in tools if t.annotations and t.annotations.readOnlyHint]
    assert reads, "Expected at least one @read_tool registered."


def test_annotation_buckets_are_consistent() -> None:
    """A tool may be read-only-non-destructive or writeable, never both.

    A ``readOnlyHint=True, destructiveHint=True`` combination is meaningless
    and indicates a misuse of the decorators. Iterating in-body instead of
    via ``@pytest.mark.parametrize`` keeps tool enumeration out of pytest's
    collection phase, which is more robust across servers that may have
    different module-import side effects.
    """
    bad: list[str] = []
    for t in _list_tools():
        ann = t.annotations
        assert ann is not None
        if ann.readOnlyHint and ann.destructiveHint:
            bad.append(t.name)
    assert not bad, (
        f"Tools with readOnlyHint=True AND destructiveHint=True: {bad}. "
        "Pick @read_tool, @write_tool, or @destructive_tool — not both ends."
    )
