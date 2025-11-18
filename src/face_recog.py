import os
import json
import numpy as np
import face_recognition
from typing import Optional, Tuple
from pathlib import Path
from .config import ENC_DB, PHOTO_DIR


# ------------------------------------------------------------
# Ensure the database file exists
# ------------------------------------------------------------
def ensure_db():
    Path(os.path.dirname(ENC_DB)).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(ENC_DB):
        with open(ENC_DB, "w") as f:
            json.dump({}, f)


# ------------------------------------------------------------
# Load the known encodings database
# ------------------------------------------------------------
def load_known_encodings(path: str = ENC_DB):
    ensure_db()
    with open(path, "r") as f:
        db = json.load(f)

    # Convert list encodings to numpy arrays
    for sid, v in db.items():
        enc_list = v.get("encodings", [])
        db[sid]["encodings"] = [np.array(e) for e in enc_list]

    return db


# ------------------------------------------------------------
# Save database safely
# ------------------------------------------------------------
def save_known_encodings(db: dict, path: str = ENC_DB):
    out = {}

    for sid, data in db.items():
        encs = data.get("encodings", [])
        encs_as_list = [e.tolist() if hasattr(e, "tolist") else e for e in encs]

        out[sid] = {
            "encodings": encs_as_list,
            "meta": data.get("meta", {})
        }

    with open(path, "w") as f:
        json.dump(out, f, indent=2)


# ------------------------------------------------------------
# Encode a single image file → returns list of 128-D vectors
# ------------------------------------------------------------
def encode_image_file(img_path: str):
    img = face_recognition.load_image_file(img_path)
    boxes = face_recognition.face_locations(img, model="hog")

    if not boxes:
        return []

    encs = face_recognition.face_encodings(img, known_face_locations=boxes)
    return [np.array(e) for e in encs]


# ------------------------------------------------------------
# Match a given face encoding to DB student IDs
# ------------------------------------------------------------
def match_face_encoding(
    encoding: np.ndarray,
    known_db: dict,
    threshold: float = 0.5
) -> Tuple[Optional[int], Optional[float]]:

    best_id = None
    best_conf = None

    for sid, v in known_db.items():
        encs = v.get("encodings", [])
        if not encs:
            continue

        # Compute face distances
        dists = face_recognition.face_distance(encs, encoding)
        min_dist = float(np.min(dists))

        # Confidence metric: convert distance to [0,1]
        conf = max(0.0, min(1.0, 1.0 - min_dist / 0.6))

        if best_conf is None or conf > best_conf:
            best_conf = conf
            best_id = sid

    if best_conf is not None and best_conf >= threshold:
        return int(best_id), float(best_conf)

    return None, None