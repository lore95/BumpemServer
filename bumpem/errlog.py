"""Error log for Claude (docs/API.md "Error log", DECISIONS D51): one JSON line per problem, one file per day in the
log folder (`errors_<YYYYMMDD>.jsonl`). Writing never raises: a broken log must not break the server."""
from __future__ import annotations

import json
import logging
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class ErrorLog:
    def __init__(self, folder: str | Path, pc: Callable[[], float]):
        self.folder, self._pc = Path(folder), pc
        self._lock = threading.Lock()
        self.recent: deque[dict[str, Any]] = deque(maxlen=500)

    def path(self, day: str | None = None) -> Path:
        return self.folder / f"errors_{day or datetime.now().strftime('%Y%m%d')}.jsonl"

    def write(self, level: str, source: str, message: str, **ctx: Any) -> None:
        e = {"wall": datetime.now().astimezone().isoformat(timespec="milliseconds"), "pc_s": round(self._pc(), 3),
             "level": level, "source": source, "message": str(message)[:4000], **ctx}
        try:
            line = json.dumps(e, default=str)
            with self._lock:
                self.recent.append(e)
                self.folder.mkdir(parents=True, exist_ok=True)
                with self.path().open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as x:                    # disk full, folder gone, …: say so in the window, carry on
            print(f"bumpem: error log not written ({x!r}): {message}", file=sys.stderr)


class _Handler(logging.Handler):
    """Python logging (uvicorn / FastAPI unhandled exceptions) → the error log."""

    def __init__(self, log: ErrorLog):
        super().__init__(logging.ERROR)
        self.log = log

    def emit(self, record: logging.LogRecord) -> None:
        tb = "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None
        self.log.write("error", "server", record.getMessage(), logger=record.name, traceback=tb)


def install(log: ErrorLog) -> Callable[[], None]:
    """Hook logging and thread exceptions; returns the undo (called at server shutdown)."""
    handler = _Handler(log)
    loggers = [logging.getLogger(), logging.getLogger("uvicorn.error")]
    for lg in loggers:
        lg.addHandler(handler)
    old_hook = threading.excepthook

    def hook(args):
        tb = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        log.write("error", "server", f"{args.exc_type.__name__} in thread {getattr(args.thread, 'name', '?')}: {args.exc_value}",
                  traceback=tb)
        old_hook(args)

    threading.excepthook = hook

    def undo() -> None:
        for lg in loggers:
            lg.removeHandler(handler)
        threading.excepthook = old_hook
    return undo
