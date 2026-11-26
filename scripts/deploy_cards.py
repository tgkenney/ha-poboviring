#!/usr/bin/env python3
"""Deploy the dashboard cards as inline Lovelace resources over HA WebSocket.

The cards under cards/ carry a `CARD_TAG` constant. Each file is uploaded as an
inline data: module resource, replacing the resource that currently holds the
same tag or creating it when absent. This is how the Rings cards are shipped:
Home Assistant storage dashboards keep resources in `.storage`, so a file copy
is not enough.

Usage:
    HA_URL=http://homeassistant.local:8123 HA_TOKEN=... \
        python3 scripts/deploy_cards.py [cards/rings-dashboard-card.js ...]
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import sys
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
CARD_DIR = ROOT / "cards"
TAG_RE = re.compile(r"CARD_TAG\s*=\s*['\"]([^'\"]+)['\"]")
INLINE_LIMIT = 24 * 1024


async def _send(ws, request_id: int, **payload) -> dict:
    await ws.send(json.dumps({"id": request_id, **payload}))
    while True:
        message = json.loads(await ws.recv())
        if message.get("id") == request_id:
            return message


async def _deploy(url: str, token: str, files: list[Path]) -> int:
    ws_url = url.rstrip("/").replace("http", "ws", 1) + "/api/websocket"
    failures = 0
    async with websockets.connect(ws_url, max_size=None) as ws:
        hello = json.loads(await ws.recv())
        if hello.get("type") != "auth_required":
            print(f"Unexpected WebSocket greeting: {hello}")
            return 1
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print(f"Authentication failed: {auth}")
            return 1

        listing = await _send(ws, 1, type="lovelace/resources")
        if not listing.get("success"):
            print(f"Could not list resources: {listing.get('error')}")
            return 1
        resources = listing.get("result") or []
        next_id = 2

        for path in files:
            source = path.read_text()
            match = TAG_RE.search(source)
            if not match:
                print(f"{path.name}: no CARD_TAG found, skipping")
                failures += 1
                continue
            marker = match.group(1)
            encoded = "data:text/javascript;base64," + base64.b64encode(
                source.encode()
            ).decode()

            target = None
            for resource in resources:
                item_url = str(resource.get("url", ""))
                if not item_url.startswith("data:text/javascript;base64,"):
                    continue
                try:
                    decoded = base64.b64decode(item_url.split(",", 1)[1]).decode()
                except (ValueError, UnicodeDecodeError):
                    continue
                if marker in decoded:
                    target = resource
                    break

            if len(source.encode()) > INLINE_LIMIT:
                print(f"{path.name}: warning: {len(source.encode())} bytes exceeds the ~24KB inline limit")

            next_id += 1
            if target and target.get("url") == encoded:
                print(f"{path.name}: already current ({target['id']})")
            elif target:
                response = await _send(
                    ws,
                    next_id,
                    type="lovelace/resources/update",
                    resource_id=target["id"],
                    res_type="module",
                    url=encoded,
                )
                ok = response.get("success")
                print(f"{path.name}: updated {target['id']} ({ok})")
                if not ok:
                    failures += 1
            else:
                response = await _send(
                    ws,
                    next_id,
                    type="lovelace/resources/create",
                    res_type="module",
                    url=encoded,
                )
                ok = response.get("success")
                created = (response.get("result") or {}).get("id")
                print(f"{path.name}: created {created} ({ok})")
                if not ok:
                    failures += 1

    return failures


def main() -> int:
    url = os.environ.get("HA_URL")
    token = os.environ.get("HA_TOKEN")
    if not url or not token:
        print("HA_URL and HA_TOKEN must be set")
        return 2

    files = [Path(arg) for arg in sys.argv[1:]] or sorted(CARD_DIR.glob("*.js"))
    if not files:
        print("No card files found")
        return 2

    failures = asyncio.run(_deploy(url, token, files))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
