"""
enroll.py - Existing enrollment endpoints integrated into new backend
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
import shutil
import datetime
from pathlib import Path

from src.face_recog import encode_image_file, load_known_encodings, save_known_encodings
from src.config import PHOTO_DIR, ENC_DB
from ..db import get_db, Database

router = APIRouter()

@router.get("/enroll", response_class=HTMLResponse)
async def enroll_form():
    """Render enrollment form"""
    html = """
    <html>
      <head>
        <style>
          body { font-family: Arial; margin: 40px; background: #f5f5f5; }
          .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          h2 { color: #333; }
          input[type="text"], input[type="file"] { width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; }
          button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
          button:hover { background: #0056b3; }
          label { font-weight: bold; color: #555; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Student Enrollment</h2>
          <p>Upload 2-6 images of the student for better accuracy.</p>

          <form action="/enroll" enctype="multipart/form-data" method="post">
              <label>Student ID:</label>
              <input name="student_id" type="text" required placeholder="Enter student ID" /><br><br>

              <label>Student Name (Optional):</label>
              <input name="student_name" type="text" placeholder="Enter student name" /><br><br>

              <label>Select Photos:</label>
              <input name="files" type="file" accept="image/*" multiple required /><br><br>

              <button type="submit">Upload & Enroll</button>
          </form>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/enroll")
async def enroll(
    student_id: str = Form(...),
    student_name: str = Form(None),
    files: list[UploadFile] = File(...),
    db: Database = Depends(get_db)
):
    """Handle enrollment submission"""
    sid = student_id.strip()

    if not sid:
        return JSONResponse({"error": "Student ID cannot be empty"}, status_code=400)

    # Create student folder
    student_folder = os.path.join(PHOTO_DIR, sid)
    Path(student_folder).mkdir(parents=True, exist_ok=True)

    saved = 0

    # Save each uploaded image file
    for f in files:
        ext = os.path.splitext(f.filename)[1] or ".jpg"
        fname = f"{int(datetime.datetime.utcnow().timestamp())}_{saved+1}{ext}"
        dst = os.path.join(student_folder, fname)

        with open(dst, "wb") as out:
            shutil.copyfileobj(f.file, out)

        saved += 1

    # Process Encodings
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

    # Update known_encodings.json
    enc_db = load_known_encodings()
    enc_db.setdefault(sid, {"encodings": [], "meta": {}})

    for e in encs:
        enc_db[sid]["encodings"].append(e.tolist())

    enc_db[sid]["meta"]["enrolled_at"] = datetime.datetime.utcnow().isoformat()
    if student_name:
        enc_db[sid]["meta"]["name"] = student_name

    save_known_encodings(enc_db)

    # Also insert into students table if DB available
    try:
        await db.execute(
            """
            INSERT INTO students (student_id, name, enrolled_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (student_id) DO UPDATE SET name = $2, enrolled_at = $3
            """,
            sid,
            student_name or f"Student {sid}",
            datetime.datetime.utcnow()
        )
    except Exception as e:
        # Non-critical error, enrollment still succeeded in JSON
        pass

    return RedirectResponse(url="/enroll?success=true", status_code=303)

@router.get("/students")
async def list_students(db: Database = Depends(get_db)):
    """List all enrolled students"""
    try:
        students = await db.fetch_all(
            "SELECT student_id, name, enrolled_at FROM students ORDER BY enrolled_at DESC"
        )
        return {"students": students}
    except:
        # Fallback to JSON file
        enc_db = load_known_encodings()
        students = []
        for sid, data in enc_db.items():
            meta = data.get("meta", {})
            students.append({
                "student_id": sid,
                "name": meta.get("name", f"Student {sid}"),
                "enrolled_at": meta.get("enrolled_at")
            })
        return {"students": students}