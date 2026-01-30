"""
인식 레이어.
- trigger: 모션 감지 시작/종료 (트리거)
- app.workers: 트리거 워커, 모드별 감지 워커 (re-export)
- ppt / youtube / game: 모드별 제스처·자세 감지
"""

from app.recognition.trigger import PostureTriggerDetector, TriggerResult
from app.workers import TriggerWorker, ModeDetectionWorker
from app.recognition.ppt import PPTDetector
from app.recognition.youtube import YouTubeDetector
from app.recognition.game import GameDetector
from app.recognition.registry import get_mode_detector

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
