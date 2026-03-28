"""Jeden textový report soubor na běh scraperu (UTF-8, složka logs/)."""

from __future__ import annotations

import os
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO


class RunReportWriter:
    def __init__(self, path: Path, file: TextIO) -> None:
        self.path = path
        self._file = file

    def write_raw(self, text: str) -> None:
        self._file.write(text)
        self._file.flush()

    def line(self, text: str = "") -> None:
        self._file.write(text + "\n")
        self._file.flush()

    def section(self, title: str) -> None:
        self.line()
        self.line(f"=== {title} ===")

    def lines(self, *parts: str) -> None:
        for p in parts:
            self.line(p)


_writer_ctx: ContextVar[RunReportWriter | None] = ContextVar(
    "run_report_writer", default=None
)


def _default_log_dir() -> Path:
    raw = os.getenv("SCRAPER_RUN_LOG_DIR", "logs")
    return Path(raw)


def init_for_run(log_dir: Path | None = None) -> Path:
    """
    Otevře nový report soubor a nastaví ho jako aktivní pro aktuální context.
    Vrací cestu k souboru.
    """
    base = (log_dir or _default_log_dir()).resolve()
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()
    path = base / f"run_{stamp}_{pid}.txt"
    f = path.open("w", encoding="utf-8")
    writer = RunReportWriter(path, f)
    _writer_ctx.set(writer)
    writer.section("Start")
    writer.line(f"Timestamp (local): {datetime.now().isoformat(timespec='seconds')}")
    return path


def append_section(title: str) -> None:
    w = _writer_ctx.get()
    if w:
        w.section(title)


def append_line(text: str = "") -> None:
    w = _writer_ctx.get()
    if w:
        w.line(text)


def append_lines(*lines: str) -> None:
    w = _writer_ctx.get()
    if w:
        w.lines(*lines)


def append_kv(label: str, value: Any) -> None:
    append_line(f"{label}: {value}")


def close_writer() -> None:
    w = _writer_ctx.get()
    if w is None:
        return
    try:
        w._file.close()
    finally:
        _writer_ctx.set(None)


def active_path() -> Path | None:
    w = _writer_ctx.get()
    return w.path if w else None
