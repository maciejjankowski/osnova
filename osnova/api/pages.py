"""HTML page routes for the Osnova frontend."""
from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

pages_router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _datetimeformat(ts: int) -> str:
    """Format a unix timestamp to a readable string."""
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def _get_templates(request: Request) -> Jinja2Templates:
    t = request.app.state.templates
    t.env.filters["datetimeformat"] = _datetimeformat
    return t


# ---------------------------------------------------------------------------
# Redirect root
# ---------------------------------------------------------------------------

@pages_router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/feed")


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

@pages_router.get("/feed", response_class=HTMLResponse, include_in_schema=False)
async def page_feed(request: Request):
    log = request.app.state.content_log
    posts = await log.get_feed(limit=50, offset=0)
    # Only show top-level posts (not comments/reshares that are replies)
    top_posts = [p for p in posts if p.content_type in ("post", "reshare", "article")]
    t = _get_templates(request)
    return t.TemplateResponse("feed.html", {
        "request": request,
        "posts": top_posts,
        "active": "feed",
    })


@pages_router.get("/feed/posts/{content_hash}/comments", response_class=HTMLResponse, include_in_schema=False)
async def page_comments(content_hash: str, request: Request):
    log = request.app.state.content_log
    comments = await log.get_comments(content_hash)
    t = _get_templates(request)
    return t.TemplateResponse("comments_partial.html", {
        "request": request,
        "comments": comments,
        "post_hash": content_hash,
    })


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------

@pages_router.get("/compose", response_class=HTMLResponse, include_in_schema=False)
async def page_compose(request: Request):
    t = _get_templates(request)
    return t.TemplateResponse("compose.html", {
        "request": request,
        "active": "compose",
    })


# ---------------------------------------------------------------------------
# Rings
# ---------------------------------------------------------------------------

@pages_router.get("/rings", response_class=HTMLResponse, include_in_schema=False)
async def page_rings(request: Request):
    rings = request.app.state.ring_manager
    stats = await rings.get_ring_stats()
    # Build peers_by_level dict for the template
    peers_by_level: dict[str, list[Any]] = {}
    for level in ("core", "inner", "middle", "outer"):
        from osnova.schemas import RingLevel
        peers = await rings.get_peers_by_ring(RingLevel(level))
        if peers:
            peers_by_level[level] = peers
    t = _get_templates(request)
    return t.TemplateResponse("rings.html", {
        "request": request,
        "stats": stats,
        "peers_by_level": peers_by_level,
        "active": "rings",
    })


@pages_router.get("/rings/list", response_class=HTMLResponse, include_in_schema=False)
async def page_rings_list(request: Request):
    """Partial - rings list only, for HTMX refresh after add/remove."""
    rings = request.app.state.ring_manager
    peers_by_level: dict[str, list[Any]] = {}
    for level in ("core", "inner", "middle", "outer"):
        from osnova.schemas import RingLevel
        peers = await rings.get_peers_by_ring(RingLevel(level))
        if peers:
            peers_by_level[level] = peers
    t = _get_templates(request)
    return t.TemplateResponse("rings_list_partial.html", {
        "request": request,
        "peers_by_level": peers_by_level,
    })


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

@pages_router.get("/identity", response_class=HTMLResponse, include_in_schema=False)
async def page_identity(request: Request):
    from osnova.crypto.identity import get_identity
    signing_key = request.app.state.signing_key
    display_name = request.app.state.display_name
    config = request.app.state.config
    identity = get_identity(signing_key, display_name)
    endpoint = f"http://{config.host}:{config.port}"
    t = _get_templates(request)
    return t.TemplateResponse("identity.html", {
        "request": request,
        "identity": identity,
        "endpoint": endpoint,
        "active": "identity",
    })


# ---------------------------------------------------------------------------
# Eject
# ---------------------------------------------------------------------------

@pages_router.get("/eject", response_class=HTMLResponse, include_in_schema=False)
async def page_eject(request: Request):
    t = _get_templates(request)
    return t.TemplateResponse("eject.html", {
        "request": request,
        "active": "eject",
    })


# ---------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------

@pages_router.get("/discover", response_class=HTMLResponse, include_in_schema=False)
async def page_discover(request: Request):
    log = request.app.state.content_log
    posts = await log.get_feed(limit=100, offset=0)
    top_posts = [p for p in posts if p.content_type in ("post", "article")]
    triads = request.app.state.triads
    received_keys = request.app.state.received_keys
    t = _get_templates(request)
    # Serialize Pydantic objects to dicts for Jinja2 (avoids unhashable-type errors)
    triads_data = [tr.model_dump() for tr in triads]
    keys_data = [k.model_dump() for k in received_keys]
    return t.TemplateResponse("discover.html", {
        "request": request,
        "active": "discover",
        "posts": top_posts,
        "triads": triads_data,
        "received_keys": keys_data,
    })
