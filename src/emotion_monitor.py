import os
import time
import json
import math
import collections
import argparse
from datetime import datetime, timezone

import numpy as np
import cv2
from PIL import Image
import torch
import face_recognition

from .config import MODEL_PATH, DEVICE, ENC_DB, SESSION_LOG
from .face_recog import load_known_encodings, match_face_encoding
from .pose_and_blink import (
    LEFT_EYE_IDX,
    RIGHT_EYE_IDX,
    eye_aspect_ratio,
    get_head_pose,
    BlinkTracker
)


# ------------------------------------------------------
# Try using MediaPipe FaceMesh (best)
# ------------------------------------------------------
USE_MEDIAPIPE = False
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    USE_MEDIAPIPE = True
    print("[INFO] MediaPipe FaceMesh loaded successfully.")
except Exception as e:
    print("[WARN] MediaPipe not available:", e)
    mp_face_mesh = None


# ------------------------------------------------------
# Fallback face detector (Haar Cascade)
# ------------------------------------------------------
cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

LABELS = ["Happy", "Sad", "Angry", "Surprise", "Fear", "Disgust", "Neutral"]


# ------------------------------------------------------
# Utilities
# ------------------------------------------------------
def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


# ------------------------------------------------------
# Load Model
# ------------------------------------------------------
def load_model(model_path, device):
    if not os.path.exists(model_path):
        raise FileNotFoundError(model_path)

    try:
        # Try TorchScript
        m = torch.jit.load(model_path, map_location=device)
        m.to(device).eval()
        return m
    except Exception:
        pass

    m = torch.load(model_path, map_location=device)
    if hasattr(m, "eval"):
        m.to(device).eval()
        return m

    raise RuntimeError("Unable to load model. If it's a state_dict, provide architecture.")


# ------------------------------------------------------
# Preprocess for model
# ------------------------------------------------------
def preprocess_face(face_bgr, input_size=(224, 224)):
    img = Image.fromarray(cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)).convert("RGB")
    img = img.resize(input_size)

    arr = np.array(img).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    arr = (arr - mean) / std
    t = torch.tensor(arr).permute(2, 0, 1).unsqueeze(0).float()
    return t


# ------------------------------------------------------
# Metrics Engine
# ------------------------------------------------------
class MetricsEngine:
    def __init__(self, short_w=30, long_w=300, ema_alpha=0.2):
        self.short_w = short_w
        self.long_w = long_w
        self.ema_alpha = ema_alpha

        self.buf = collections.deque(maxlen=short_w)
        self.long_buf = collections.deque(maxlen=long_w)

        self.center_vel = collections.deque(maxlen=short_w)
        self.prev_center = None

        self.eng_ema = None

    def push(self, probs, top, box, ear=None, pose=None):
        self.buf.append({
            "probs": probs,
            "top": top,
            "box": box,
            "ear": ear,
            "pose": pose,
            "ts": time.time()
        })
        self.long_buf.append(self.buf[-1])

        # Movement detection
        if box:
            x, y, w, h = box
            cx = x + w / 2
            cy = y + h / 2
            if self.prev_center is None:
                dist = 0.0
            else:
                dx = cx - self.prev_center[0]
                dy = cy - self.prev_center[1]
                dist = math.hypot(dx, dy)

            norm_dist = dist / max(1.0, (w + h) / 2)
            self.center_vel.append(norm_dist)
            self.prev_center = (cx, cy)
        else:
            self.center_vel.append(0.0)

    def compute(self):
        if not self.buf:
            return {}

        probs_arr = np.array([b["probs"] for b in self.buf])
        top_labels = [b["top"] for b in self.buf]

        cur = probs_arr[-1]
        pH, pSad, pAng, pSur, pFea, pDis, pNeu = cur.tolist()

        # ----------------- Attentiveness -----------------
        A_raw = 0.6 * pSur + 0.35 * pNeu - 0.25 * (pSad + pAng + pFea + pDis)
        Att = float(np.clip(A_raw, 0, 1))

        # ----------------- Positivity --------------------
        P_raw = pH * 1 + pNeu * 0.2 - pSad * 0.6 - pAng * 0.6 - pDis * 0.5 - pFea * 0.4 + pSur * 0.15
        Pos = float(np.clip((P_raw + 0.6) / 1.6, 0, 1))

        # ----------------- Engagement --------------------
        Eng_raw = 0.7 * Att + 0.3 * Pos
        if self.eng_ema is None:
            self.eng_ema = Eng_raw
        else:
            self.eng_ema = (1 - self.ema_alpha) * self.eng_ema + self.ema_alpha * Eng_raw
        Eng = float(np.clip(self.eng_ema, 0, 1))

        # ----------------- Boredom -----------------------
        neutral_sad = sum(1 for t in top_labels if t in ("Neutral", "Sad")) / len(top_labels)
        mean_probs = np.mean(probs_arr, axis=0)
        ent = -np.sum(mean_probs * np.log(mean_probs + 1e-12)) / np.log(len(mean_probs))
        low_var = 1 - ent
        Boredom = float(np.clip(neutral_sad * 0.8 + low_var * 0.2, 0, 1))

        # ----------------- Frustration -------------------
        base = pAng + pFea + pDis
        prev_mean = np.mean((probs_arr[:-1, 2] + probs_arr[:-1, 4] + probs_arr[:-1, 5])) if len(probs_arr) > 1 else 0
        trend = max(0.0, base - prev_mean)
        Fr = float(np.clip(0.6 * base + 0.4 * trend, 0, 1))

        # ----------------- Volatility ---------------------
        stds = np.std(probs_arr, axis=0)
        Vol = float(np.clip(np.mean(stds) / 0.5, 0, 1))

        # ----------------- Distraction --------------------
        move = float(np.mean(self.center_vel))
        move = float(np.clip(move * 3.0, 0, 1))
        Distraction = float(np.clip(0.6 * move + 0.4 * (1 - Att), 0, 1))

        # ----------------- Fatigue ------------------------
        ears = [b["ear"] for b in self.buf if b["ear"] is not None]
        if eyes_closed := (len(ears) > 0):
            avg_ear = np.mean(ears)
            Fatigue = float(np.clip(1.0 - (avg_ear - 0.10) / 0.25, 0, 1))
        else:
            Fatigue = 0.0

        # ----------------- Risk Score ---------------------
        if len(self.long_buf) > 10:
            long_tops = [b["top"] for b in self.long_buf]
            lf = sum(1 for t in long_tops if t in ("Neutral", "Sad")) / len(long_tops)
            long_probs = np.array([b["probs"] for b in self.long_buf])
            long_vol = float(np.mean(np.std(long_probs, axis=0)))
            Risk = float(np.clip(0.5 * lf + 0.3 * Fr + 0.2 * np.clip(long_vol / 0.5, 0, 1), 0, 1))
        else:
            Risk = float(np.clip(0.5 * Boredom + 0.3 * Fr + 0.2 * Vol, 0, 1))

        return {
            "attentiveness": Att,
            "positivity": Pos,
            "engagement": Eng,
            "boredom": Boredom,
            "frustration": Fr,
            "volatility": Vol,
            "distraction": Distraction,
            "fatigue": Fatigue,
            "risk": Risk
        }


# ------------------------------------------------------
# Logging
# ------------------------------------------------------
def log_record(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ------------------------------------------------------
# Prediction from Model
# ------------------------------------------------------
def predict_from_model(model, tensor, device):
    model.eval()
    with torch.no_grad():
        out = model(tensor.to(device))
        if isinstance(out, dict):
            for key in ("logits", "pred", "out"):
                if key in out:
                    logits = out[key]
                    break
            else:
                for v in out.values():
                    if torch.is_tensor(v):
                        logits = v
                        break
        else:
            logits = out

        logits = logits.squeeze(0).cpu().numpy()
        probs = softmax(logits)
        idx = int(np.argmax(probs))
        return probs.tolist(), LABELS[idx], float(probs[idx])


# ------------------------------------------------------
# Main Real-Time Monitoring Loop
# ------------------------------------------------------
def main(
    model_path=MODEL_PATH,
    enc_db_path=ENC_DB,
    session_log=SESSION_LOG,
    device=DEVICE,
    video_src=0,
    match_thresh=0.5,
    log_every=5,
    device_id="default",
    output_mode="log"
):

    print("[INFO] Loading emotion model...")
    model = load_model(model_path, device=device)

    print("[INFO] Loading face encodings database...")
    known_db = load_known_encodings(enc_db_path)

    print("[INFO] Opening camera...")
    cap = cv2.VideoCapture(video_src)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam/video!")

    metrics_engine = MetricsEngine()
    blink_tracker = BlinkTracker()

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        h, w = frame.shape[:2]

        # ---------------- FACE DETECTION ----------------
        faces = cascade.detectMultiScale(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        # ---------------- LANDMARKS / POSE / BLINK -----
        landmarks = None
        if USE_MEDIAPIPE:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = mp_face_mesh.process(rgb)
            if res.multi_face_landmarks:
                landmarks = res.multi_face_landmarks[0].landmark

        # If cascade found faces, use largest
        if len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        elif landmarks is not None:
            x, y, fw, fh = 0, 0, w, h
        else:
            cv2.imshow("AiSMS Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        face_crop = frame[y:y+fh, x:x+fw]

        # ---------------- EMOTION MODEL -----------------
        tensor = preprocess_face(face_crop)
        probs, emotion, emo_conf = predict_from_model(model, tensor, device)

        # ---------------- FACE RECOGNITION --------------
        student_id = None
        face_conf = None
        try:
            rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb_face, model="hog")
            if locs:
                encs = face_recognition.face_encodings(rgb_face, locs)
                if encs:
                    student_id, face_conf = match_face_encoding(encs[0], known_db, threshold=match_thresh)
        except:
            pass

        # ---------------- HEAD POSE + BLINK --------------
        ear = None
        head_pose = (0, 0, 0)

        if landmarks:
            try:
                ear_l = eye_aspect_ratio(landmarks, LEFT_EYE_IDX, w, h)
                ear_r = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX, w, h)
                ear = (ear_l + ear_r) / 2
                head_pose = get_head_pose(landmarks, w, h)
                blink_tracker.update(ear)
            except:
                pass

        # ---------------- METRICS ------------------------
        metrics_engine.push(probs, emotion, (x, y, fw, fh), ear=ear, pose=head_pose)
        metrics = metrics_engine.compute()

        # ---------------- LOGGING ------------------------
        if frame_idx % log_every == 0:
            record = {
                "timestamp": now_iso(),
                "student_id": student_id,
                "face_match_confidence": face_conf,
                "emotion": emotion,
                "emotion_confidence": emo_conf,
                "probabilities": {k: float(v) for k, v in zip(LABELS, probs)},
                "metrics": metrics,
                "ear": ear,
                "head_pose": {
                    "yaw": head_pose[0],
                    "pitch": head_pose[1],
                    "roll": head_pose[2]
                },
                "source_device": device_id
            }
            if output_mode == "json":
                print(json.dumps(record), flush=True)
            else:
                log_record(session_log, record)

        # ---------------- DRAW ON SCREEN -----------------
        cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

        header = f"{emotion} ({emo_conf*100:.1f}%)"
        if student_id:
            header = f"ID:{student_id} - {header}"

        cv2.putText(frame, header, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(frame,
                    f"Eng:{metrics['engagement']*100:.0f}%  Att:{metrics['attentiveness']*100:.0f}%",
                    (x, y + fh + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 255), 1)

        cv2.putText(frame,
                    f"Bor:{metrics['boredom']*100:.0f}%  Fr:{metrics['frustration']*100:.0f}%",
                    (x, y + fh + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

        # EAR + head pose for debugging
        if ear is not None:
            cv2.putText(frame, f"EAR:{ear:.2f}",
                        (x, y + fh + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        yaw, pitch, roll = head_pose
        cv2.putText(frame, f"Yaw:{yaw:.1f}  P:{pitch:.1f}",
                    (x, y + fh + 78), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        if output_mode != "json":
            cv2.imshow("AiSMS Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    if output_mode != "json":
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=MODEL_PATH)
    parser.add_argument("--enc-db", default=ENC_DB)
    parser.add_argument("--session-log", default=SESSION_LOG)
    parser.add_argument("--device", default=DEVICE)
    parser.add_argument("--video-src", default="0")
    parser.add_argument("--match-thresh", type=float, default=0.5)
    parser.add_argument("--log-every", type=int, default=5)
    parser.add_argument("--device-id", default="default")
    parser.add_argument("--output-mode", choices=["log", "json"], default="log")

    args = parser.parse_args()

    video_source = args.video_src
    try:
        video_source = int(video_source)
    except ValueError:
        pass

    main(
        model_path=args.model_path,
        enc_db_path=args.enc_db,
        session_log=args.session_log,
        device=args.device,
        video_src=video_source,
        match_thresh=args.match_thresh,
        log_every=args.log_every,
        device_id=args.device_id,
        output_mode=args.output_mode,
    )