"""Step 1, FETCH: read each company's official job board through its provider's public API.

Every source returns RawPost dicts with the same fields, so the rest of the pipeline does not
care where a post came from. A board that fails never stops the run.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources import ashby, greenhouse, lever, smartrecruiters, workday

FETCHERS: dict[str, Callable[..., list[RawPost]]] = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
}
DETAIL: dict[str, Callable[[RawPost], RawPost]] = {
    "smartrecruiters": smartrecruiters.detail,
    "workday": workday.detail,
}


def board_key(post: RawPost) -> str:
    return f"{post['source']}:{post['board']}"


def fetch_all(companies: dict[str, Any], delay: float = 0.5,
              log: Callable[[str], None] = print) -> tuple[list[RawPost], dict[str, bool]]:
    """Return (posts, status). status["greenhouse:acme"] is True when that board answered.

    Remembering which boards answered matters: if a board is down, its posts must NOT be
    treated as closed (that bug would wipe good posts).
    """
    posts: list[RawPost] = []
    status: dict[str, bool] = {}

    def attempt(key: str, call: Callable[[], list[RawPost]]) -> None:
        try:
            posts.extend(call())
            status[key] = True
        except Exception as e:  # noqa: BLE001 - one bad board must never stop the run
            status[key] = False
            if "429" in str(e):    # the site asked us to stop: respect it, no retries
                log(f"  ! {key}: site refused automated requests (429), skipped")
            else:
                log(f"  ! {key}: {type(e).__name__} {str(e)[:80]}")

    for kind, fn in FETCHERS.items():
        for slug in companies.get(kind) or []:
            args = (slug, delay) if kind == "smartrecruiters" else (slug,)
            attempt(f"{kind}:{slug}", lambda fn=fn, args=args: fn(*args))
            time.sleep(delay)
    if companies.get("workday_enabled"):
        for entry in companies.get("workday") or []:
            attempt(f"workday:{entry['tenant']}", lambda entry=entry: workday.fetch(entry, delay))
    return posts, status
