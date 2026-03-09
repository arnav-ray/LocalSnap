# CLAUDE.md — LocalSnap

> Project-level instructions for Claude Code sessions working on this repository.

---

## Project Summary

LocalSnap is a **self-hosted, offline photo library manager** that runs entirely on the local machine.
It replaces cloud-based photo apps (Google Photos, iCloud) for users who want full data ownership.

Access is via a browser pointed at `http://127.0.0.1:5000`. Nothing leaves the machine.

---

## Irrevocable Privacy Constraint

**This rule overrides everything else. It cannot be relaxed, routed around, or "temporarily" bypassed.**

- ❌ Never add code that uploads photos, metadata, embeddings, or any user data to any external server
- ❌ Never add analytics, telemetry, remote error reporting, or usage tracking of any kind
- ❌ Never call any external API with photo content or face embeddings
- ❌ Never add LLM-based features that process images remotely
- ✅ All ML inference must use locally-stored ONNX model files
- ✅ All writes go to local disk only (sidecar JSON files, gallery_data.js)

If a requested feature cannot be implemented without violating this constraint, say so clearly instead of finding a workaround.

---

## Architecture

```
Browser (localhost:5000)
    │
    ▼
Flask server (server.py)
    ├── Serves static UI (index.html, gallery_data.js)
    ├── Serves /Library/ — raw photo files
    ├── /api/detect_faces    → OpenCV YuNet ONNX model
    ├── /api/tag_face        → SFace embedding extraction + sidecar write
    └── /api/scan_status     → live progress polling (SSE or interval)

Photo Library (local disk, configurable path)
    └── photo.jpg
    └── photo.jpg.supplemental-metadata.json   ← Google Takeout sidecar
    └── photo.jpg.supplem.json                  ← legacy name (see Known Bugs)
```

### Key design decisions (do not reverse without good reason)

| Decision | Rationale |
|----------|-----------|
| Flask over FastAPI | Simpler for contributors unfamiliar with async; no performance bottleneck at local scale |
| Vanilla JS + Tailwind over React | No build step, no npm required to run; low friction for non-developers |
| ONNX models (YuNet + SFace) | No internet dependency post-download; deterministic, auditable behaviour |
| JSON sidecars for metadata | Preserves compatibility with Google Takeout format; no database to manage |
| Cosine similarity threshold 0.363 | SFace paper's recommended value — document any changes with evidence |

---

## Known Bugs

### 1. Sidecar filename mismatch (build_gallery.py)

`_read_sidecar()` in `snippets/build_gallery.py` looks for `.supplem.json`:

```python
sidecar = photo_file.parent / (photo_file.name + ".supplem.json")
```

Google Takeout exports sidecars as `.supplemental-metadata.json`. This causes metadata (timestamps, GPS) to silently not load for most photos. The correct path is:

```python
sidecar = photo_file.parent / (photo_file.name + ".supplemental-metadata.json")
```

Fix this before any work that depends on timestamps or GPS being correct.

### 2. Non-recursive library scan

`build_gallery.py` uses `library.iterdir()`, which only scans the **top-level directory**.
Google Takeout exports are nested (year/album subdirectories). This means most photos are missed.

Replace with `library.rglob("*")` filtered by extension.

### 3. Video files excluded from `_build_photo_item` type check

`_build_photo_item` labels items as `"video"` only for `.mp4` / `.mov`, but the initial file loop in `build_gallery_index` filters to `.jpg`, `.jpeg`, `.png` only — so videos are never ingested at all. The two lists are inconsistent.

---

## File Structure

```
/
├── README.md               — User-facing project documentation
├── PRIVACY.md              — Privacy design principles
├── CLAUDE.md               — This file (Claude Code instructions)
├── server.py               — Flask application entry point
├── build_gallery.py        — Scans library, writes gallery_data.js
├── download_models.py      — One-time ONNX model downloader
├── index.html              — Frontend gallery UI
├── gallery_data.js         — Generated index (do not hand-edit)
├── models/                 — ONNX model files (gitignored)
│   ├── face_detection_yunet.onnx
│   └── face_recognition_sface.onnx
├── snippets/               — Illustrative code samples (not production)
│   ├── build_gallery.py
│   ├── face_detection.py
│   └── metadata_recovery.py
└── Library/                — User's photo collection (gitignored)
```

> `models/` and `Library/` are gitignored. Never commit ONNX model binaries or photo files.

---

## Running Locally

```bash
pip install flask flask-cors opencv-python

# One-time model download
python download_models.py

# Build the gallery index from the Library/ folder
python build_gallery.py

# Start the server
python server.py
# → http://127.0.0.1:5000
```

---

## Face Recognition Pipeline (overview)

1. User opens a photo, types a person's name
2. **YuNet** runs multi-scale detection → returns bounding boxes
3. User clicks the correct face box
4. **SFace** extracts a 128-dim geometric embedding of that crop
5. Background scanner compares embedding to every photo in library via cosine similarity (threshold 0.363)
6. Matches are written to `local_people` key in the JSON sidecar file
7. Gallery rebuilds — person appears in People view

---

## What to Avoid

- Do not add `requirements.txt` with pinned cloud SDK packages (boto3, google-cloud-*, azure-*)
- Do not suggest rewriting the frontend in React/Vue — build step overhead contradicts the local-first principle
- Do not add a database (SQLite etc.) without first considering whether JSON sidecars can be extended
- Do not modify the face similarity threshold without citing a benchmark
- Do not remove or weaken the privacy guardrail section in README.md or PRIVACY.md

---

## Context

This project was built using AI-assisted development (Antigravity / Google Gemini). The original author directed architecture and privacy decisions but did not write the code personally. When making changes, maintain the transparency about AI authorship documented in README.md.
