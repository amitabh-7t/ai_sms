"""
enroll_api.py

Browser-based enrollment:
  - GET  /enroll      -> load upload form
  - POST /enroll      -> upload photos + student_id

All uploaded photos saved under:
    data/enrollment_photos/<student_id>/

Encodings stored in:
    data/known_encodings.json
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

import os
import shutil
import datetime
from pathlib import Path

from ..face_recog import encode_image_file, load_known_encodings, save_known_encodings
from ..config import PHOTO_DIR, ENC_DB


router = APIRouter()


# --------------------------------------------------------
# Enrollment Form Page
# --------------------------------------------------------
@router.get("/enroll", response_class=HTMLResponse)
async def enroll_form():
    html = """
    <html>
      <body style="font-family: Arial; margin: 40px;">
        <h2>Student Enrollment</h2>
        <p>Upload 2-6 images of the student for better accuracy.</p>

        <form action="/enroll" enctype="multipart/form-data" method="post">
            <label>Student ID:</label>
            <input name="student_id" type="text" required /><br><br>

            <label>Select Photos:</label>
            <input name="files" type="file" accept="image/*" 
                   multiple required /><br><br>

            <button type="submit" 
                style="padding:8px 16px; background:#007bff; color:white;
                       border:none; border-radius:5px; cursor:pointer;">
                Upload & Enroll
            </button>
        </form>

      </body>
    </html>
    """
    return HTMLResponse(content=html)


# --------------------------------------------------------
# Handle Enrollment Submission
# --------------------------------------------------------
@router.post("/enroll")
async def enroll(
    student_id: str = Form(...),
    files: list[UploadFile] = File(...)
):
    sid = student_id.strip()

    if not sid:
        return JSONResponse({"error": "Student ID cannot be empty"}, status_code=400)

    # Create student folder
    student_folder = os.path.join(PHOTO_DIR, sid)
    Path(student_folder).mkdir(parents=True, exist_ok=True)

    saved = 0

    # -----------------------------
    # Save each uploaded image file
    # -----------------------------
    for f in files:
        ext = os.path.splitext(f.filename)[1] or ".jpg"
        fname = f"{int(datetime.datetime.utcnow().timestamp())}_{saved+1}{ext}"
        dst = os.path.join(student_folder, fname)

        with open(dst, "wb") as out:
            shutil.copyfileobj(f.file, out)

        saved += 1

    # -----------------------------
    # Process Encodings
    # -----------------------------
    encs = []
    for file in os.listdir(student_folder):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(student_folder, file)
            found_encs = encode_image_file(img_path)
            encs.extend(found_encs)

    if not encs:
        return JSONResponse({
            "warning": "No valid faces detected in uploaded images."
        }, status_code=200)

    # -----------------------------
    # Update known_encodings.json
    # -----------------------------
    db = load_known_encodings()
    db.setdefault(sid, {"encodings": [], "meta": {}})

    for e in encs:
        db[sid]["encodings"].append(e.tolist())

    db[sid]["meta"]["enrolled_at"] = datetime.datetime.utcnow().isoformat()

    save_known_encodings(db)

    # Redirect back to form
    return RedirectResponse(url="/enroll", status_code=303)