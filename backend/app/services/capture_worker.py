import asyncio
import json
import logging
import os
import subprocess
import threading
import time
import sys
from pathlib import Path
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PYTHON_EXECUTABLE = sys.executable


class CaptureWorker:
    """
    Manages a single capture subprocess (emotion_monitor) for a device.
    Streams JSON events via stdout and forwards them to an async callback.
    """

    def __init__(
        self,
        device_id: str,
        config: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        on_event: Callable[[Dict[str, Any]], asyncio.Future],
    ):
        self.device_id = device_id
        self.config = config or {}
        self.loop = loop
        self.on_event = on_event

        self.process: Optional[subprocess.Popen] = None
        self.stdout_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.events_count = 0
        self.error_count = 0
        self.started_at: Optional[float] = None
        self.session_id: Optional[int] = None

    def start(self, session_id: int) -> bool:
        """Start the capture process."""
        if self.is_running:
            logger.warning("Capture already running for %s", self.device_id)
            return False

        video_src = str(self.config.get("video_src", 0))
        model_path = self.config.get(
            "model_path",
            str(Path(PROJECT_ROOT, "models", "emotion_model.pt")),
        )
        match_thresh = str(self.config.get("match_thresh", 0.5))
        log_every = str(self.config.get("log_every", 5))

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "src.emotion_monitor",
            "--video-src",
            video_src,
            "--model-path",
            model_path,
            "--device-id",
            self.device_id,
            "--match-thresh",
            match_thresh,
            "--log-every",
            log_every,
            "--output-mode",
            "json",
        ]

        env = os.environ.copy()
        env.setdefault("PYTHONPATH", str(PROJECT_ROOT))

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
        except Exception as exc:
            logger.error("Failed to launch capture for %s: %s", self.device_id, exc)
            return False

        self.session_id = session_id
        self.is_running = True
        self.started_at = time.time()
        self.events_count = 0
        self.error_count = 0

        self.stdout_thread = threading.Thread(
            target=self._read_stdout, name=f"{self.device_id}-stdout", daemon=True
        )
        self.stdout_thread.start()

        self.stderr_thread = threading.Thread(
            target=self._read_stderr, name=f"{self.device_id}-stderr", daemon=True
        )
        self.stderr_thread.start()

        logger.info(
            "Capture started for %s (session %s, pid=%s)",
            self.device_id,
            session_id,
            self.process.pid,
        )
        return True

    def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return
        try:
            for line in self.process.stdout:
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event.setdefault("source_device", self.device_id)
                    future = asyncio.run_coroutine_threadsafe(
                        self.on_event(event), self.loop
                    )
                    future.add_done_callback(self._handle_future_result)
                    self.events_count += 1
                except json.JSONDecodeError:
                    logger.debug("[%s] %s", self.device_id, line)
                except Exception as exc:
                    logger.error("Error handling event from %s: %s", self.device_id, exc)
                    self.error_count += 1
        finally:
            self.is_running = False
            logger.info("Capture stdout ended for %s", self.device_id)

    def _handle_future_result(self, future: asyncio.Future):
        try:
            future.result()
        except Exception as exc:
            logger.error("Event callback error for %s: %s", self.device_id, exc)
            self.error_count += 1

    def _read_stderr(self):
        if not self.process or not self.process.stderr:
            return
        for line in self.process.stderr:
            if not line:
                continue
            logger.warning("[%s][stderr] %s", self.device_id, line.rstrip())

    def stop(self) -> bool:
        if not self.process or not self.is_running:
            return False
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Force killing capture for %s", self.device_id)
            self.process.kill()
            self.process.wait()
        except Exception as exc:
            logger.error("Error stopping capture for %s: %s", self.device_id, exc)
            return False
        finally:
            self.is_running = False

        if self.stdout_thread:
            self.stdout_thread.join(timeout=2)
        if self.stderr_thread:
            self.stderr_thread.join(timeout=2)

        logger.info("Capture stopped for %s", self.device_id)
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "session_id": self.session_id,
            "is_running": self.is_running,
            "events_count": self.events_count,
            "error_count": self.error_count,
            "started_at": self.started_at,
            "uptime": time.time() - self.started_at if self.started_at else 0,
            "pid": self.process.pid if self.process else None,
        }

