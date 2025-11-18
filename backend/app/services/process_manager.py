import asyncio
import logging
from typing import Dict, Optional, Any

from ..db import db
from ..models import EventData
from ..api.ingest import insert_event
from .publisher import publish_event
from .capture_worker import CaptureWorker

logger = logging.getLogger(__name__)


class ProcessManager:
    """Singleton manager for capture workers (one per device)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.workers: Dict[str, CaptureWorker] = {}
        return cls._instance

    async def start_capture(self, device_id: str, config: Dict[str, Any], session_id: int) -> bool:
        if device_id in self.workers and self.workers[device_id].is_running:
            logger.warning("Capture already running for %s", device_id)
            return False

        loop = asyncio.get_running_loop()

        async def on_event(event_payload: Dict[str, Any]):
            try:
                event_payload.setdefault("timestamp", event_payload.get("timestamp"))
                event_payload.setdefault("source_device", device_id)
                event = EventData(**event_payload)
            except Exception as exc:
                logger.error("Invalid event payload from %s: %s", device_id, exc)
                return

            try:
                success = await insert_event(event, db)
                if success:
                    await publish_event(device_id, event.dict())
                else:
                    logger.error("Failed to insert event for %s", device_id)
            except Exception as exc:
                logger.error("Error handling event for %s: %s", device_id, exc)

        worker = CaptureWorker(device_id, config, loop, on_event)
        success = worker.start(session_id)
        if success:
            self.workers[device_id] = worker
            logger.info("Capture worker registered for %s", device_id)
        return success

    def stop_capture(self, device_id: str) -> bool:
        worker = self.workers.get(device_id)
        if not worker:
            return False
        success = worker.stop()
        if success:
            self.workers.pop(device_id, None)
        return success

    def get_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        worker = self.workers.get(device_id)
        if not worker:
            return None
        return worker.get_status()

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        return {device_id: worker.get_status() for device_id, worker in self.workers.items()}

    def stop_all(self):
        for device_id in list(self.workers.keys()):
            try:
                self.stop_capture(device_id)
            except Exception as exc:
                logger.error("Failed to stop capture for %s: %s", device_id, exc)


process_manager = ProcessManager()

