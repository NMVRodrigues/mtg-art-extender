#!/usr/bin/env python3
"""Fetch Magic card images from the Scryfall API."""


import json
import re
import sys
import time
from pathlib import Path


import requests


BASE = "https://api.scryfall.com"
# Border colors that count as "bordered" (vs borderless showcase prints)
BORDERED = {"black", "white", "silver", "gold", "yellow"}


def _img(card: dict, v: str = "png") -> str:
   """Image URL for card; dual-faced cards use first face."""
   uris = card.get("image_uris") or card["card_faces"][0]["image_uris"]
   return uris[v]



def _slug(s: str) -> str:
   """Safe filename from card name."""
   return re.sub(r"[^\w\-]", "_", s).strip("_")


def _get(url: str) -> dict:
   """Fetch JSON from URL."""
   r = requests.get(url, timeout=15)
   r.raise_for_status()
   return r.json()

def _all_prints(uri: str) -> list[dict]:
   """All prints of a card via prints_search_uri; paginates."""
   out, url = [], uri
   while url:
       d = _get(url)
       out.extend(d["data"])
       url = d.get("next_page")
       time.sleep(0.1)  # Rate limit
   return out


def _load_resume(path: Path) -> tuple[list[tuple[dict, dict]], int]:
   """Load (pairs, last_completed_page) from resume file; ([], 1) if missing/invalid."""
   if not path.exists():
       return [], 1
   try:
       data = json.loads(path.read_text())
       pairs = [tuple(p) for p in data.get("pairs", [])]
       page = data.get("page", 1)
       return pairs, page
   except (json.JSONDecodeError, OSError):
       return [], 1


def _save_resume(path: Path, pairs: list[tuple[dict, dict]], page: int) -> None:
   """Save pairs and last completed page for resume."""
   path.parent.mkdir(parents=True, exist_ok=True)
   path.write_text(json.dumps({"page": page, "pairs": list(pairs)}, indent=2))


def borderless_pairs(resume_path: Path | None = None) -> list[tuple[dict, dict]]:
   """Cards with both borderless and bordered prints; returns (borderless, bordered) tuples."""
   pairs, page, pages = [], 1, None
   if resume_path:
       pairs, last_page = _load_resume(resume_path)
       if pairs:
           page = last_page + 1
           print(f"Resuming: {len(pairs)} pairs loaded, continuing from page {page}")
   while True:
       d = requests.get(f"{BASE}/cards/search", params={"q": "border:borderless", "unique": "prints", "page": page}, timeout=15).json()
       if d.get("object") == "error":
           raise RuntimeError(d.get("details", str(d)))
       if pages is None:
           total = d.get("total_cards") or 0
           pages = (total // 175) + 1 if total else "?"
       print(f"Page {page}/{pages} — {len(pairs)} pairs so far")
       for c in d.get("data", []):
           if c.get("border_color") != "borderless" or not c.get("prints_search_uri"):
               continue
           br = next((p for p in _all_prints(c["prints_search_uri"]) if p.get("border_color") in BORDERED), None)
           if br:
               pairs.append((c, br))
       if resume_path:
           _save_resume(resume_path, pairs, page)
       if not d.get("has_more"):
           break
       page += 1
       time.sleep(0.1)
   return pairs

def download_pairs(out: Path | None = None, v: str = "large", limit: int | None = None, resume_path: Path | None = None) -> list[tuple[Path, Path]]:
   """Download borderless + bordered images; limit caps pairs (for testing)."""
   out = out or Path("data/scryfall_borderless_pairs")
   out.mkdir(parents=True, exist_ok=True)
   resume = resume_path or out / "resume.json"
   pairs = borderless_pairs(resume_path=resume)
   if limit:
       pairs = pairs[:limit]
   result = []
   for i, (bl, br) in enumerate(pairs):
       slug = _slug(bl.get("name", "unknown"))
       bl_path, br_path = out / f"{slug}_borderless.jpg", out / f"{slug}_bordered.jpg"
       if bl_path.exists() and br_path.exists():
           result.append((bl_path, br_path))
           print(f"[{i + 1}/{len(pairs)}] {bl.get('name')} (skip, exists)")
           continue
       for card, p in [(bl, bl_path), (br, br_path)]:
           r = requests.get(_img(card, v), timeout=15)
           r.raise_for_status()
           p.write_bytes(r.content)
       result.append((bl_path, br_path))
       print(f"[{i + 1}/{len(pairs)}] {bl.get('name')}")
       time.sleep(0.1)
   return result


if __name__ == "__main__":
   # Usage: python scryfall_images.py [limit] [out_dir]
   # Resume: pairs + page saved to out_dir/resume.json; delete to start fresh
   limit = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
   out = next((Path(a) for a in sys.argv[1:] if not a.isdigit()), None)
   paths = download_pairs(out=out, limit=limit)
   print(f"\n{len(paths)} pairs → {paths[0][0].parent if paths else 'N/A'}")
