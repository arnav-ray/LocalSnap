# Privacy Policy & Data Guardrails

This document defines the absolute, irrevocable privacy rules for this project.

## Core Principle

**All data stays on your machine. Always.**

## Specific Rules

### What this software NEVER does:
- ❌ Upload photos, thumbnails, or any image data to any server
- ❌ Send metadata (filenames, dates, GPS coordinates, people names) to any remote service
- ❌ Share face embeddings or facial geometry data with any third party
- ❌ Connect to any cloud AI API (OpenAI, Google Cloud Vision, AWS Rekognition, etc.)
- ❌ Contribute any personal data to LLM training datasets
- ❌ Log, track, or transmit user activity of any kind

### What this software ALWAYS does:
- ✅ Process all images exclusively on the local CPU/GPU
- ✅ Store all data (embeddings, tags, metadata) in local files only
- ✅ Serve the web interface exclusively on localhost (127.0.0.1)
- ✅ Use only offline ONNX models for facial recognition

## Irrevocability

> These rules are permanent design constraints, not configuration options.  
> They cannot be removed, modified, or bypassed by any future commit,  
> dependency update, or configuration change.  
> There are no exceptions to these rules under any circumstances.

## Open Source Model Licenses

- **YuNet** (face detection): OpenCV Zoo, Apache 2.0
- **SFace** (face recognition): OpenCV Zoo, Apache 2.0
- **Haar Cascades**: OpenCV, Apache 2.0

All models are downloaded once and stored locally. They do not phone home.
