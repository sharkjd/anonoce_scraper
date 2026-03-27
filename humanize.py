import asyncio
import random
from typing import TypedDict


class Viewport(TypedDict):
    width: int
    height: int


_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 "
    "Mobile/15E148 Safari/604.1",
)

_VIEWPORTS: tuple[Viewport, ...] = (
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1600, "height": 900},
    {"width": 1920, "height": 1080},
)

HUMAN_SCROLL_JS = """
(() => {
  const jitter = (min, max) => Math.random() * (max - min) + min;
  const firstScroll = Math.floor(jitter(220, 620));
  window.scrollTo({ top: firstScroll, behavior: "smooth" });
  setTimeout(() => {
    if (Math.random() > 0.35) {
      const secondScroll = firstScroll + Math.floor(jitter(140, 460));
      window.scrollTo({ top: secondScroll, behavior: "smooth" });
    }
  }, Math.floor(jitter(500, 1500)));
})();
""".strip()


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


def browser_headers(url: str, referer: str | None = None) -> dict[str, str]:
    return {
        "User-Agent": random_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.7,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Referer": referer or url,
    }


def random_viewport() -> Viewport:
    return random.choice(_VIEWPORTS)


def bounded_jitter(min_sec: float, max_sec: float) -> float:
    lo = max(0.0, min_sec)
    hi = max(lo, max_sec)
    if lo == hi:
        return lo
    mean = (lo + hi) / 2.0
    std_dev = max((hi - lo) / 6.0, 0.05)
    for _ in range(6):
        sample = random.gauss(mean, std_dev)
        if lo <= sample <= hi:
            return sample
    return random.uniform(lo, hi)


async def human_delay(min_sec: float, max_sec: float) -> float:
    duration = bounded_jitter(min_sec, max_sec)
    await asyncio.sleep(duration)
    return duration


async def reading_pause(min_sec: float = 2.0, max_sec: float = 6.0) -> float:
    return await human_delay(min_sec, max_sec)
