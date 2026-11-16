"""Saved perturbation patterns (docs/API.md "Perturbation patterns", DECISIONS D50): directions + step gaps, made once
and used by a block for every participant. One JSON file per pattern; a saved pattern is never overwritten."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .geometry import normalize

NAME = r"^[A-Za-z0-9_-]{1,40}$"


class Item(BaseModel):
    angle_deg: float
    gap_steps: int = Field(ge=1, le=1000, description="steps after the previous perturbation (first: after the warm-up)")


class Pattern(BaseModel):
    name: str = Field(pattern=NAME)
    note: str = Field("", max_length=200)
    items: list[Item] = Field(min_length=1, max_length=500)
    rules: dict[str, Any] = Field(default_factory=dict, description="how it was generated (kept, not used)")
    created: str | None = None


class PatternStore:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder)

    def _path(self, name: str) -> Path:
        if not re.match(NAME, name):
            raise KeyError(name)
        return self.folder / f"{name}.json"

    def get(self, name: str) -> Pattern:
        p = self._path(name)
        if not p.is_file():
            raise KeyError(name)
        return Pattern(**json.loads(p.read_text(encoding="utf-8")))

    def list(self) -> list[dict[str, Any]]:
        out = []
        for p in self.folder.glob("*.json") if self.folder.is_dir() else []:
            try:
                pat = Pattern(**json.loads(p.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                continue                          # not a pattern file: skipped
            gaps = [i.gap_steps for i in pat.items]
            out.append({"name": pat.name, "n": len(pat.items), "created": pat.created, "note": pat.note,
                        "angles": sorted({i.angle_deg for i in pat.items}), "gap_min": min(gaps), "gap_max": max(gaps)})
        return sorted(out, key=lambda d: d["created"] or "", reverse=True)

    def save(self, pat: Pattern) -> Pattern:
        p = self._path(pat.name)
        if p.exists():                            # also catches another case on Windows / macOS
            raise FileExistsError(pat.name)
        pat = pat.model_copy(update={"created": datetime.now().astimezone().isoformat(timespec="seconds"),
                                     "items": [Item(angle_deg=normalize(i.angle_deg), gap_steps=i.gap_steps) for i in pat.items]})
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(pat.model_dump(), indent=1), encoding="utf-8")
        os.replace(tmp, p)
        return pat
