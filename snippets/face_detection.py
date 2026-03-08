"""
Snippet: Offline Face Detection + Recognition Pipeline
========================================================
Face detection and recognition runs 100% on the local machine
using OpenCV's ONNX-based DNN models.

No internet connection required after the one-time model download.
No images are ever sent to any external service.

NOTE: This is a simplified illustration — not production-ready code.
"""

import cv2
import numpy as np


# --- Model Initialization (run once at server startup) ---

def load_models(models_dir: str):
    """
    Loads the face detection and recognition models from local ONNX files.
    Models are downloaded once and stored locally.
    """
    detector = cv2.FaceDetectorYN.create(
        f"{models_dir}/face_detection_yunet.onnx",
        "",
        (320, 320),
        score_threshold=0.5,   # 0.5 catches partial/angled faces
        nms_threshold=0.3,
        top_k=5000
    )
    recognizer = cv2.FaceRecognizerSF.create(
        f"{models_dir}/face_recognition_sface.onnx", ""
    )
    return detector, recognizer


# --- Face Detection ---

def detect_faces(img: np.ndarray, detector) -> list[tuple[int,int,int,int]]:
    """
    Detects all faces in an image.
    Returns a list of (x, y, width, height) bounding boxes.
    
    Uses multi-scale detection to catch both close-up and distant faces.
    """
    orig_h, orig_w = img.shape[:2]
    all_boxes = []

    # Run at multiple scales for better coverage
    for max_dim in [orig_w, 1280, 640]:
        scale = min(1.0, max_dim / max(orig_w, orig_h))
        w = max(int(orig_w * scale), 32)
        h = max(int(orig_h * scale), 32)
        work = cv2.resize(img, (w, h)) if scale < 1.0 else img

        detector.setInputSize((w, h))
        _, faces = detector.detect(work)

        if faces is not None:
            for f in faces:
                # Scale coordinates back to original image space
                box = (
                    int(f[0] / scale), int(f[1] / scale),
                    int(f[2] / scale), int(f[3] / scale)
                )
                all_boxes.append(box)

    return _deduplicate_boxes(all_boxes)


def _deduplicate_boxes(boxes: list) -> list:
    """Removes overlapping bounding boxes using IoU (Intersection over Union)."""
    unique = []
    for x, y, w, h in boxes:
        is_dup = any(
            _iou((x,y,w,h), u) > 0.5 for u in unique
        )
        if not is_dup:
            unique.append((x, y, w, h))
    return unique


def _iou(a, b) -> float:
    """Computes Intersection over Union of two boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(ax, bx); iy = max(ay, by)
    iw = min(ax+aw, bx+bw) - ix
    ih = min(ay+ah, by+bh) - iy
    if iw <= 0 or ih <= 0:
        return 0.0
    i_area = iw * ih
    return i_area / (aw*ah + bw*bh - i_area)


# --- Face Embedding Extraction ---

FACE_SIZE = 112  # SFace expects 112x112 pixel input

def extract_embedding(img: np.ndarray, box: tuple, recognizer) -> np.ndarray | None:
    """
    Crops the face region and extracts a 128-dimensional geometric embedding.
    This embedding represents the unique facial geometry — not a photo.
    
    Embeddings are stored locally and never transmitted.
    """
    x, y, w, h = box
    ih, iw = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(iw, x+w), min(ih, y+h)
    if x2 <= x1 or y2 <= y1:
        return None
    face_crop = cv2.resize(img[y1:y2, x1:x2], (FACE_SIZE, FACE_SIZE))
    return recognizer.feature(face_crop)


def are_same_person(
    embedding_a: np.ndarray,
    embedding_b: np.ndarray,
    recognizer,
    threshold: float = 0.363
) -> bool:
    """
    Compares two face embeddings using cosine similarity.
    Returns True if similarity exceeds the threshold.
    
    Threshold of 0.363 is the SFace paper's recommended value for
    a good balance between precision and recall.
    """
    similarity = recognizer.match(
        embedding_a, embedding_b,
        cv2.FaceRecognizerSF_FR_COSINE
    )
    return similarity >= threshold
