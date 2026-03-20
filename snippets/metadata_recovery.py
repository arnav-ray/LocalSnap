"""
Snippet: Metadata Recovery from Photo Export Sidecars
=======================================================
When exporting photos from a cloud service, each photo typically comes
with a JSON sidecar file containing the original timestamp and GPS data.

This snippet shows how to read that sidecar and restore the metadata.

NOTE: This is a simplified illustration — not production-ready code.
"""

import json
import os
from datetime import datetime
from pathlib import Path


def read_sidecar(photo_path: str) -> dict | None:
    """
    Reads the JSON sidecar file alongside a photo.
    Returns the metadata dict, or None if no sidecar exists.
    """
    sidecar_path = photo_path + ".supplemental-metadata.json"
    if not os.path.exists(sidecar_path):
        return None

    try:
        with open(sidecar_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def extract_date_taken(meta: dict) -> datetime | None:
    """
    Extracts the original photo timestamp from the sidecar.
    Cloud exports store this as a Unix timestamp in photoTakenTime.
    """
    taken = meta.get("photoTakenTime", {})
    timestamp = taken.get("timestamp")
    if timestamp:
        return datetime.fromtimestamp(int(timestamp))
    return None


def extract_gps(meta: dict) -> tuple[float, float] | None:
    """
    Extracts GPS coordinates from the sidecar.
    Returns (latitude, longitude) or None.
    """
    geo = meta.get("geoData", {})
    lat = geo.get("latitude", 0.0)
    lng = geo.get("longitude", 0.0)
    # Coordinates of (0, 0) mean no GPS data was recorded
    if lat == 0.0 and lng == 0.0:
        return None
    # Reject out-of-range coordinates — prevents bad data from poisoning the map view
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return None
    return (lat, lng)


# --- Example usage ---
if __name__ == "__main__":
    photo = "example_photo.jpg"
    meta = read_sidecar(photo)

    if meta:
        date = extract_date_taken(meta)
        gps = extract_gps(meta)

        print(f"Photo: {photo}")
        print(f"  Date taken:  {date}")
        print(f"  GPS:         {gps}")
    else:
        print("No metadata sidecar found.")
