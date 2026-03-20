# Security & Governance Guide — LocalSnap

> This document describes the data flows, PII handling rules, and security
> checklist for LocalSnap. It is a companion to PRIVACY.md (which defines the
> irrevocable no-upload constraint) and CLAUDE.md (which defines architecture
> decisions for AI-assisted development).

---

## Personal Data Inventory

| Data Type | Sensitivity | Where Stored | Transmitted? |
|-----------|-------------|--------------|--------------|
| Photo files (.jpg / .png / .mp4) | HIGH | `Library/` on local disk | Never |
| GPS coordinates (lat/lng) | HIGH | JSON sidecars + `gallery_data.js` | Never |
| Timestamps (photo taken time) | MEDIUM | JSON sidecars + `gallery_data.js` | Never |
| Person names (face tags) | HIGH (PII) | JSON sidecars + `gallery_data.js` | Never |
| Face embeddings (128-dim vectors) | HIGH (biometric) | JSON sidecars only | Never |
| Filenames | MEDIUM | `gallery_data.js` | Never |

All data lives on the local filesystem. Nothing is transmitted to any external server.

---

## Data Flow

```
Library/*.jpg  →  build_gallery.py  →  gallery_data.js  →  browser (localhost:5000)
                       ↑                      ↑
              JSON sidecars             served by Flask
              (GPS, names,              (read-only)
               embeddings)

User tags face  →  /api/tag_face  →  SFace ONNX (local)  →  sidecar JSON (local write)
```

No step in this flow contacts an external host.

---

## Git Safety Rules

The following paths are in `.gitignore` and **must never be committed**:

- `Library/` — contains photos and JSON sidecars with GPS, faces, names
- `models/` — ONNX binaries (no PII, but large; downloaded once locally)
- `gallery_data.js` — derived index that aggregates all PII fields
- `.env` / `*.key` / `*.pem` — secrets must never enter version control

If you see any of these appearing in `git status`, do **not** commit them.

---

## Flask Server Security Checklist

When implementing `server.py`, every item below is required:

### Path Traversal Prevention
- [ ] All file-serving endpoints must resolve paths with `Path.resolve()` and
      verify the result is a child of `Library/` before opening the file.
- [ ] Reject any path containing `..` sequences before resolving.

### CORS
- [ ] `flask-cors` must be configured with `origins=["http://127.0.0.1:5000"]`
      — never `origins="*"` or a remote host.

### Input Validation
- [ ] `/api/detect_faces`: validate that the submitted filename exists inside
      `Library/` after resolving; enforce a file-size limit.
- [ ] `/api/tag_face`: validate person name — strip leading/trailing whitespace,
      reject empty strings, enforce a maximum length (e.g. 100 chars), disallow
      path-separator characters (`/`, `\`, `..`).
- [ ] `/api/scan_status`: no user-controlled input; return only progress
      counters, never file paths or person names.

### Error Handling
- [ ] Register a Flask `@app.errorhandler` for 400, 404, and 500 that returns
      a safe JSON message — never a raw Python traceback or file path.
- [ ] Do not log person names, GPS coordinates, or face embeddings to any log
      file or stdout in production.

### HTTP Security Headers
Add the following response headers to every route:

```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["Content-Security-Policy"] = "default-src 'self'"
response.headers["Cache-Control"] = "no-store"  # for /api/* endpoints only
```

### Request Limits
- [ ] Set `MAX_CONTENT_LENGTH` in Flask config to limit upload size (e.g. 50 MB).
- [ ] Add a timeout on OpenCV/ONNX inference to prevent DoS via large images.

---

## Atomic Sidecar Writes

When updating a JSON sidecar (e.g. adding `local_people`), use an atomic write
pattern to prevent corruption if the process is interrupted:

```python
import os, json, tempfile
from pathlib import Path

def update_sidecar(sidecar_path: Path, data: dict) -> None:
    tmp = sidecar_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, sidecar_path)  # atomic on POSIX
```

---

## Dependency Policy

Allowed:
- `flask`, `flask-cors` — local web server
- `opencv-python` — local CV/ML inference
- Standard library only beyond the above

Prohibited (will be rejected in code review):
- Any package from `boto3`, `google-cloud-*`, `azure-*` families
- Any package that establishes outbound network connections to non-localhost hosts
- Any analytics or error-reporting SDK (Sentry, Datadog, etc.)

---

## Encryption at Rest

LocalSnap does not encrypt sidecar files or `gallery_data.js` at rest.
This is intentional for simplicity, but users with high-sensitivity libraries
should store the `Library/` directory on an encrypted volume (e.g. macOS
FileVault, Linux LUKS, VeraCrypt).

---

## Audit Log

| Date | Auditor | Finding | Resolution |
|------|---------|---------|------------|
| 2026-03-20 | Claude (claude-sonnet-4-6) | Sidecar filename mismatch — `.supplem.json` vs `.supplemental-metadata.json` | Fixed in `snippets/build_gallery.py:56` |
| 2026-03-20 | Claude (claude-sonnet-4-6) | Non-recursive library scan — `iterdir()` misses nested dirs | Fixed: replaced with `rglob("*")` |
| 2026-03-20 | Claude (claude-sonnet-4-6) | No path validation on `library_path`/`output_path` | Fixed: added `resolve()` + type checks |
| 2026-03-20 | Claude (claude-sonnet-4-6) | Unreachable video type check — `.mp4`/`.mov` filtered before type branch | Fixed: added video extensions to allow-list |
| 2026-03-20 | Claude (claude-sonnet-4-6) | `json.load()` without error handling in metadata_recovery.py | Fixed: wrapped in `try/except` |
| 2026-03-20 | Claude (claude-sonnet-4-6) | GPS coordinates not range-validated | Fixed: added bounds check |
| 2026-03-20 | Claude (claude-sonnet-4-6) | Missing `.gitignore` — `Library/` and `models/` could be committed | Fixed: created `.gitignore` |
| 2026-03-20 | Claude (claude-sonnet-4-6) | No CORS/security-header/input-validation guidance for server.py | Fixed: documented in this file |

**Privacy compliance verdict: PASS** — no external data transmission found in any code path.
