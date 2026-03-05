#!/usr/bin/env python3
"""Fetch Magic card images from the Scryfall API."""


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




def borderless_pairs() -> list[tuple[dict, dict]]:
   """Cards with both borderless and bordered prints; returns (borderless, bordered) tuples."""
   pairs, page = [], 1
   while True:
       d = requests.get(f"{BASE}/cards/search", params={"q": "border:borderless", "unique": "prints", "page": page}, timeout=15).json()
       if d.get("object") == "error":
           raise RuntimeError(d.get("details", str(d)))
       
       total = d.get("total_cards") or 0
       pages = (total // 175) + 1 if total else "?"
       print(f"Page {page}/{pages} — {len(pairs)} pairs so far")
      
       for c in d.get("data", []):
           if c.get("border_color") != "borderless" or not c.get("prints_search_uri"):
               continue
           # Find a bordered print of the same card
           br = next((p for p in _all_prints(c["prints_search_uri"]) if p.get("border_color") in BORDERED), None)
           if br:
               pairs.append((c, br))
       if not d.get("has_more"):
           break
       page += 1
       time.sleep(0.1)  # Scryfall rate limit
   return pairs




def download_pairs(out: Path | None = None, v: str = "large", limit: int | None = None) -> list[tuple[Path, Path]]:
   """Download borderless + bordered images; limit caps pairs (for testing)."""
   out = out or Path("data/scryfall_borderless_pairs")
   out.mkdir(parents=True, exist_ok=True)
   pairs = borderless_pairs()[:limit] if limit else borderless_pairs()
   result = []
   for i, (bl, br) in enumerate(pairs):
       slug = _slug(bl.get("name", "unknown"))
       bl_path, br_path = out / f"{slug}_borderless.jpg", out / f"{slug}_bordered.jpg"
       for card, p in [(bl, bl_path), (br, br_path)]:
           r = requests.get(_img(card, v), timeout=15)
           r.raise_for_status()
           p.write_bytes(r.content)
       result.append((bl_path, br_path))
       print(f"[{i + 1}/{len(pairs)}] {bl.get('name')}")
       time.sleep(0.1)  # Rate limit
   return result




if __name__ == "__main__":
   # Usage: python scryfall_images.py [limit] [out_dir]
   limit = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
   out = next((Path(a) for a in sys.argv[1:] if not a.isdigit()), None)
   paths = download_pairs(out=out, limit=limit)
   print(f"\n{len(paths)} pairs → {paths[0][0].parent if paths else 'N/A'}")

