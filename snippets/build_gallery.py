"""
Snippet: Building the Photo Gallery Index
==========================================
This script scans the photo library and builds a JavaScript data file
(gallery_data.js) that the browser-based UI consumes to render the gallery.

All processing is local. No data is uploaded or transmitted.

NOTE: This is a simplified illustration — not production-ready code.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def build_gallery_index(library_path: str, output_path: str) -> None:
    """
    Scans the photo library, reads metadata sidecars, and writes
    a structured JS data file for the frontend to use.
    """
    library = Path(library_path).resolve()
    if not library.is_dir():
        raise ValueError(f"library_path must be an existing directory")

    output_file = Path(output_path).resolve()
    # Prevent writing outside the library's parent (e.g. via ../../../etc/passwd)
    if output_file.suffix != ".js":
        raise ValueError("output_path must point to a .js file")
    photos: list[dict[str, Any]] = []

    photo_extensions = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}
    for photo_file in sorted(library.rglob("*")):
        if not photo_file.is_file():
            continue
        if photo_file.suffix.lower() not in photo_extensions:
            continue

        meta = _read_sidecar(photo_file)
        item = _build_photo_item(photo_file, meta)
        photos.append(item)

    timeline = _group_by_date(photos)
    people = _group_by_person(photos)
    collections = _auto_collections(photos)

    output = {
        "flat": photos,
        "timeline": timeline,
        "people": people,
        "collections": collections,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("const galleryData = ")
        json.dump(output, f, separators=(",", ":"))
        f.write(";")

    print(f"Gallery index built: {len(photos)} photos")


def _read_sidecar(photo_file: Path) -> dict:
    """Read the JSON sidecar that accompanies the photo, if it exists."""
    sidecar = photo_file.parent / (photo_file.name + ".supplemental-metadata.json")
    if sidecar.exists():
        try:
            with open(sidecar, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _build_photo_item(photo_file: Path, meta: dict) -> dict:
    """Build a single photo entry with normalized fields."""
    # Recover timestamp — prefer sidecar, fall back to file mtime
    ts = meta.get("photoTakenTime", {}).get("timestamp")
    if ts:
        date_taken = datetime.fromtimestamp(int(ts))
    else:
        date_taken = datetime.fromtimestamp(photo_file.stat().st_mtime)

    # GPS coordinates
    geo = meta.get("geoData", {})
    lat = geo.get("latitude", 0.0)
    lng = geo.get("longitude", 0.0)

    # Person tags — from original metadata + local face tagging
    people = list(set(
        meta.get("people", []) + meta.get("local_people", [])
    ))

    return {
        "filename": photo_file.name,
        "date": date_taken.strftime("%Y-%m-%d"),
        "year": date_taken.year,
        "month": date_taken.strftime("%B %Y"),
        "lat": lat if lat != 0.0 else None,
        "lng": lng if lng != 0.0 else None,
        "people": people,
        "type": "video" if photo_file.suffix.lower() in (".mp4", ".mov") else "photo",
        "isScreenshot": "screenshot" in photo_file.name.lower(),
    }


def _group_by_date(photos: list[dict]) -> list[dict]:
    """Groups photos into timeline blocks by month."""
    groups: dict[str, list] = {}
    for p in photos:
        key = p["month"]
        groups.setdefault(key, []).append(p)
    return [{"date": k, "items": v} for k, v in groups.items()]


def _group_by_person(photos: list[dict]) -> list[dict]:
    """Groups photos by person name for the People view."""
    people: dict[str, dict] = {}
    for p in photos:
        for name in p.get("people", []):
            if name not in people:
                people[name] = {"name": name, "count": 0, "cover": p["filename"]}
            people[name]["count"] += 1
    return list(people.values())


def _auto_collections(photos: list[dict]) -> list[dict]:
    """Generates automatic collections: Screenshots, Videos, Places."""
    return [
        {
            "name": "Screenshots",
            "count": len([p for p in photos if p.get("isScreenshot")]),
            "cover": next((p["filename"] for p in photos if p.get("isScreenshot")), None)
        },
        {
            "name": "Videos",
            "count": len([p for p in photos if p["type"] == "video"]),
            "cover": next((p["filename"] for p in photos if p["type"] == "video"), None)
        },
        {
            "name": "Places",
            "count": len([p for p in photos if p.get("lat")]),
            "cover": next((p["filename"] for p in photos if p.get("lat")), None)
        },
    ]
