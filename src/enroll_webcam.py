"""
enroll_webcam.py

Enroll students using your system’s webcam.
Captures multiple images, stores them inside:

    data/enrollment_photos/<student_id>/

Extracts 128-d encodings using face_recognition and
appends to known_encodings.json.

Controls:
    c -> capture photo
    a -> toggle auto-capture mode
    q -> finish + encode

Run:
    python -m src.enroll_webcam
"""

import os
import time
import json
from pathlib import Path

import cv2
from .face_recog import encode_image_file, load_known_encodings, save_known_encodings
from .config import PHOTO_DIR, ENC_DB


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def main():
    print("\n--- Student Enrollment (Webcam) ---")

    ensure_dir(PHOTO_DIR)

    student_id = input("Enter student ID (numeric/string): ").strip()
    if not student_id:
        print("[ERROR] Student ID required!")
        return

    student_folder = os.path.join(PHOTO_DIR, student_id)
    ensure_dir(student_folder)

    print(f"[INFO] Student folder: {student_folder}")

    # ----------------------------
    # Start webcam
    # ----------------------------
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("[ERROR] Cannot open webcam")

    print("\nControls:")
    print("   c -> capture image")
    print("   a -> toggle auto-capture mode")
    print("   q -> save & quit\n")

    auto_mode = False
    auto_interval = 2.5
    last_auto = time.time()

    count = len([
        f for f in os.listdir(student_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to capture frame.")
            break

        display = frame.copy()

        cv2.putText(display, f"ID: {student_id}   Captures: {count}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (255, 255, 255), 2)

        if auto_mode:
            cv2.putText(display, f"AUTO MODE ({auto_interval}s)",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 0), 2)

        cv2.imshow("Enrollment - Press c/a/q", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            filename = f"{int(time.time())}_{count+1}.jpg"
            cv2.imwrite(os.path.join(student_folder, filename), frame)
            count += 1
            print(f"[INFO] Captured: {filename}")

        elif key == ord('a'):
            auto_mode = not auto_mode
            print(f"[INFO] Auto mode: {auto_mode}")

        elif key == ord('q'):
            print("[INFO] Exiting & saving encodings...")
            break

        # Auto capture
        if auto_mode and (time.time() - last_auto) >= auto_interval:
            filename = f"{int(time.time())}_{count+1}.jpg"
            cv2.imwrite(os.path.join(student_folder, filename), frame)
            count += 1
            last_auto = time.time()
            print(f"[AUTO] Captured: {filename}")

    cap.release()
    cv2.destroyAllWindows()

    # ----------------------------------------------------
    # Encode all captured images
    # ----------------------------------------------------
    print("[INFO] Encoding images...")

    encs = []
    for f in os.listdir(student_folder):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(student_folder, f)
            found_encs = encode_image_file(img_path)
            encs.extend(found_encs)

    if not encs:
        print("[ERROR] No face encodings found. Try again with better lighting.")
        return

    # ----------------------------------------------------
    # Update database
    # ----------------------------------------------------
    db = load_known_encodings()
    db.setdefault(student_id, {"encodings": [], "meta": {}})

    for e in encs:
        db[student_id]["encodings"].append(e.tolist())

    import datetime
    db[student_id]["meta"]["enrolled_at"] = datetime.datetime.utcnow().isoformat()

    save_known_encodings(db)

    print(f"[SUCCESS] Saved {len(encs)} encodings for student {student_id}.")
    print(f"[INFO] Check file: {ENC_DB}")
    print("--- Enrollment Completed ---\n")


if __name__ == "__main__":
    main()