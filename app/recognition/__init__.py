"""
인식 레이어.
- trigger: 모션 감지 시작/종료 (트리거)
- app.workers: 트리거 워커, 모드별 감지 워커 (re-export)
- ppt / youtube / game: 모드별 제스처·자세 감지
"""

from app.recognition.trigger import PostureTriggerDetector, TriggerResult
from app.recognition.ppt import PPTDetector
from app.recognition.youtube import YouTubeDetector
from app.recognition.game import GameDetector
from app.recognition.registry import get_mode_detector

def __getattr__(name):
    if name == "TriggerWorker":
        from app.workers.trigger_worker import TriggerWorker
        return TriggerWorker
    if name == "ModeDetectionWorker":
        from app.workers.mode_detection_worker import ModeDetectionWorker
        return ModeDetectionWorker
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "PostureTriggerDetector",
    "TriggerResult",
    "TriggerWorker",
    "ModeDetectionWorker",
    "PPTDetector",
    "YouTubeDetector",
    "GameDetector",
    "get_mode_detector",
]
