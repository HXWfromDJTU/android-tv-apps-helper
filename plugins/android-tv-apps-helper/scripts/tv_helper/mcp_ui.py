"""Optional official SDK transport; browser mode has no third-party dependencies."""
from __future__ import annotations

import asyncio
import json
import secrets
import threading
from pathlib import Path
from typing import Any

from .html_ui import HtmlController, html_document
from .session import SessionStore

RESOURCE = "ui://android-tv-apps-helper/choice-v1.html"


def create_server(session_root: Path):
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.types import CallToolResult, TextContent
    except ImportError as error:
        raise ValueError("MCP UI requires optional mcp==1.26.0. Install scripts/mcp-requirements.txt in a venv, or use serve-ui (stdlib only).") from error
    root = session_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("session-root must be a local session directory")
    mcp = FastMCP("Android TV Apps Helper", log_level="ERROR")
    sessions: dict[str, HtmlController] = {}
    paths: dict[Path, str] = {}
    browsers = {}

    def controller(key):
        if key not in sessions:
            raise ValueError("Unknown session; call tv_ui_show first.")
        return sessions[key]

    @mcp.resource(RESOURCE, mime_type="text/html;profile=mcp-app",
                  meta={"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}}})
    def choice_page() -> str:
        return html_document()

    @mcp.resource("tv-state://{session_key}", mime_type="application/json")
    def state_resource(session_key: str) -> str:
        return json.dumps({**controller(session_key).snapshot(), "session_key": session_key}, ensure_ascii=False)

    @mcp.tool(meta={"ui": {"resourceUri": RESOURCE}}, structured_output=False)
    def tv_ui_show(session_path: str) -> Any:
        """Show HTML choices for an existing supported desktop session. Wait for real clicks; never synthesize submissions. If no embedded UI renders, call tv_ui_browser."""
        path = Path(session_path).expanduser().resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Session must be an existing file inside configured session-root.")
        if path not in paths:
            key = secrets.token_urlsafe(24)
            sessions[key] = HtmlController(SessionStore(path))
            paths[path] = key
        key = paths[path]
        data = {**controller(key).snapshot(), "session_key": key}
        return CallToolResult(content=[TextContent(type="text", text="点选页面已准备。实际显示后等待用户提交；未渲染则调用 tv_ui_browser 打开本地点选页面。")],
                              structuredContent=data, _meta={"ui": {"resourceUri": RESOURCE}})

    @mcp.tool(structured_output=True)
    def tv_ui_state(session_key: str) -> dict[str, Any]:
        """Read the authoritative state. Execute only action_required and record actual evidence with the harness; never infer success from a click."""
        return {**controller(session_key).snapshot(), "session_key": session_key}

    @mcp.tool(meta={"ui": {"visibility": ["app"]}}, structured_output=True)
    def tv_ui_submit(session_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        """UI-only: validate the actual user click bound to the displayed presentation. Does not run device operations."""
        return {**controller(session_key).submit(payload), "session_key": session_key}

    @mcp.tool(structured_output=True)
    async def tv_ui_wait(session_key: str, after: str, timeout: float = 25) -> dict[str, Any]:
        """Wait up to 30 seconds for a real click/state change. Unchanged means unanswered; continue waiting, never default to a choice."""
        result = await asyncio.to_thread(controller(session_key).wait, after, timeout)
        return {**result, "session_key": session_key}

    @mcp.tool(structured_output=True)
    def tv_ui_browser(session_key: str) -> dict[str, Any]:
        """Provide a private loopback point-and-click page if the host cannot embed MCP Apps. Keep waiting with tv_ui_wait; no text-menu fallback."""
        from .html_server import ChoiceServer
        if session_key not in browsers:
            server = ChoiceServer(controller(session_key))
            browsers[session_key] = server
            threading.Thread(target=server.serve_forever, daemon=True).start()
        return {"url": browsers[session_key].url, **controller(session_key).snapshot(), "session_key": session_key}

    return mcp
