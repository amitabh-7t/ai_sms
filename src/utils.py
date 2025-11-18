"""
utils.py

Small CLI utilities for working with the project files:
 - tail: tail last N lines of session log
 - to-csv: convert newline-delimited JSON log to CSV
 - summary: quick per-student aggregation (avg engagement, boredom, risk)
 - show-last: pretty-print last N JSON records

Usage examples:
  python -m src.utils tail --lines 20
  python -m src.utils to-csv --out session_logs.csv
  python -m src.utils summary --minutes 30
  python -m src.utils show-last --n 5
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from .config import SESSION_LOG, ENC_DB
import pandas as pd

def tail_lines(path, n=10):
    if not os.path.exists(path):
        print("Log file not found:", path)
        return
    with open(path, "rb") as f:
        # efficient tail for files
        avg_line_length = 200
        to_read = n * avg_line_length
        try:
            f.seek(-to_read, os.SEEK_END)
        except OSError:
            f.seek(0)
        data = f.read().decode(errors="ignore").splitlines()
    lines = data[-n:]
    for l in lines:
        print(l)

def load_json_lines(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                # skip malformed lines but print a message
                print("Warning: skipping malformed JSON line.")
    return out

def to_csv(path=SESSION_LOG, out="session_logs.csv"):
    records = load_json_lines(path)
    if not records:
        print("No records found in", path)
        return
    df = pd.json_normalize(records)
    df.to_csv(out, index=False)
    print("Wrote", len(df), "rows to", out)

def show_last(path=SESSION_LOG, n=5):
    recs = load_json_lines(path)
    if not recs:
        print("No records.")
        return
    for r in recs[-n:]:
        ts = r.get("timestamp")
        sid = r.get("student_id")
        emo = r.get("emotion")
        eng = r.get("metrics", {}).get("engagement")
        print(f"{ts} | id:{sid} | emo:{emo} | eng:{eng}")
        # pretty print probabilities if present
        probs = r.get("probabilities")
        if probs:
            probs_str = ", ".join([f"{k}:{v:.2f}" for k,v in probs.items()])
            print("  probs:", probs_str)

def aggregate_by_student(path=SESSION_LOG, minutes: int = 60):
    recs = load_json_lines(path)
    if not recs:
        print("No records.")
        return
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    filtered = []
    for r in recs:
        ts = r.get("timestamp")
        try:
            t = datetime.fromisoformat(ts)
        except Exception:
            continue
        if t >= cutoff:
            filtered.append(r)
    if not filtered:
        print("No records in the last", minutes, "minutes.")
        return
    # compute per-student aggregations
    stats = {}
    for r in filtered:
        sid = r.get("student_id") or "unknown"
        m = r.get("metrics", {})
        stats.setdefault(sid, {"count":0, "eng_sum":0.0, "bored_sum":0.0, "risk_sum":0.0})
        stats[sid]["count"] += 1
        stats[sid]["eng_sum"] += m.get("engagement", 0.0)
        stats[sid]["bored_sum"] += m.get("boredom", 0.0)
        stats[sid]["risk_sum"] += m.get("risk", 0.0)
    # print summary
    print(f"Aggregated over last {minutes} minutes:")
    for sid, vals in stats.items():
        c = vals["count"]
        print(f"Student {sid} | samples: {c} | avg_eng:{vals['eng_sum']/c:.3f} | avg_bored:{vals['bored_sum']/c:.3f} | avg_risk:{vals['risk_sum']/c:.3f}")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_tail = sub.add_parser("tail", help="Tail last N lines of session log")
    p_tail.add_argument("--lines", type=int, default=10)
    p_tail.add_argument("--path", type=str, default=SESSION_LOG)

    p_csv = sub.add_parser("to-csv", help="Convert session log to CSV")
    p_csv.add_argument("--path", type=str, default=SESSION_LOG)
    p_csv.add_argument("--out", type=str, default="session_logs.csv")

    p_show = sub.add_parser("show-last", help="Show last N records")
    p_show.add_argument("--n", type=int, default=5)
    p_show.add_argument("--path", type=str, default=SESSION_LOG)

    p_agg = sub.add_parser("summary", help="Aggregate metrics per student")
    p_agg.add_argument("--minutes", type=int, default=60)
    p_agg.add_argument("--path", type=str, default=SESSION_LOG)

    args = parser.parse_args()

    if args.cmd == "tail":
        tail_lines(args.path, args.lines)
    elif args.cmd == "to-csv":
        to_csv(args.path, args.out)
    elif args.cmd == "show-last":
        show_last(args.path, args.n)
    elif args.cmd == "summary":
        aggregate_by_student(args.path, args.minutes)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()