"""
Backend app package initializer.

Ensures the project root is on sys.path so that modules in the top-level
`src` package (capture/edge code) can be imported by the FastAPI backend.
"""

import os
import sys
from pathlib import Path

# /Users/amitabh/Desktop/V2_AiSMS/ai_sms/backend/app -> project root (../..)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if PROJECT_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, PROJECT_ROOT.as_posix())

