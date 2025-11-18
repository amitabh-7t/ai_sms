import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "models", "emotion_model.pt"))
PHOTO_DIR = os.environ.get("PHOTO_DIR", os.path.join(BASE_DIR, "data", "enrollment_photos"))
ENC_DB = os.environ.get("ENC_DB", os.path.join(BASE_DIR, "data", "known_encodings.json"))
SESSION_LOG = os.environ.get("SESSION_LOG", os.path.join(BASE_DIR, "data", "session_data.jsonl"))
# Mac often uses MPS (Metal Performance Shaders) instead of CUDA, but we'll default to CPU if CUDA isn't found.
DEVICE = "cuda" if (os.environ.get("USE_CUDA","0")=="1") else "cpu"
