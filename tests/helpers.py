from __future__ import annotations

import asyncio

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
