"""
효과음 재생 워커 — QThread에서 MP3 재생. 재생 로직·워커·API 통합.
"""

import os
import queue
import shutil
import subprocess
import sys
from typing import Optional

from PyQt6.QtCore import QThread

import config

# PyQt6 QtMultimedia (선택)
_Player: Optional[type] = None
_AudioOutput: Optional[type] = None
_QUrl: Optional[type] = None

try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

    _Player = QMediaPlayer
    _AudioOutput = QAudioOutput
    _QUrl = QUrl
except ImportError:
    _Player = _AudioOutput = _QUrl = None

_players: list = []
_worker: Optional["SoundPlaybackWorker"] = None


def start_playback_worker() -> None:
    """재생 워커 스레드 시작. main에서 앱 기동 후 한 번 호출."""
    global _worker
    if _worker is not None:
        return
    _worker = SoundPlaybackWorker()
    _worker.start()


def stop_playback_worker() -> None:
    """재생 워커 스레드 정지. main에서 aboutToQuit 시 호출."""
    global _worker
    if _worker is not None:
        _worker.stop()
        _worker.wait(2000)
        _worker = None


def play_trigger_start() -> None:
    """모션 감지 시작 효과음 재생."""
    _enqueue_play(config.ASSETS_DIR, "motion-trigger-start.mp3")


def play_trigger_stop() -> None:
    """모션 감지 종료 효과음 재생."""
    _enqueue_play(config.ASSETS_DIR, "motion-trigger-stop.mp3")


def play_mode_sound(mode: str) -> None:
    """모드 전환 시 해당 모드 효과음 재생 (PPT / YOUTUBE / GAME)."""
    mode_upper = (mode or "").upper()
    filename = f"mode-{mode_upper.lower()}.mp3"
    _enqueue_play(config.ASSETS_DIR, filename)


def _enqueue_play(assets_dir: str, filename: str) -> None:
    path = os.path.join(assets_dir, filename)
    if not os.path.isfile(path):
        return
    if _worker is not None:
        _worker.enqueue(path)
    else:
        _play_mp3(path)


def _play_mp3(path: str) -> None:
    if not os.path.isfile(path):
        return
    if _Player is not None and _AudioOutput is not None and _QUrl is not None:
        _play_qt(path)
    else:
        _play_subprocess(path)


def _play_qt(path: str) -> None:
    try:
        player = _Player()
        audio_output = _AudioOutput()
        player.setAudioOutput(audio_output)
        player.setSource(_QUrl.fromLocalFile(path))
        player.play()
        _players.append(player)

        def _cleanup():
            try:
                _players.remove(player)
            except ValueError:
                pass

        player.mediaStatusChanged.connect(
            lambda s: _cleanup() if s == _Player.MediaStatus.EndOfMedia else None
        )
    except Exception:
        _play_subprocess(path)


def _play_subprocess(path: str) -> None:
    """시스템 플레이어 (macOS afplay, Ubuntu ffplay 등)."""
    cmd: Optional[list[str]] = None
    if sys.platform == "darwin":
        if shutil.which("afplay"):
            cmd = ["afplay", path]
    elif sys.platform == "linux":
        if shutil.which("ffplay"):
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
        elif shutil.which("mpg123"):
            cmd = ["mpg123", "-q", path]
    if cmd:
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=(sys.platform == "darwin"),
            )
        except (FileNotFoundError, OSError):
            pass


class SoundPlaybackWorker(QThread):
    """효과음 재생 QThread. 경로 큐를 받아 워커 스레드에서 _play_subprocess 호출."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path_queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=32)
        self._running = True

    def enqueue(self, path: str) -> None:
        try:
            self._path_queue.put_nowait(path)
        except queue.Full:
            pass

    def run(self) -> None:
        while self._running:
            try:
                path = self._path_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if path is None:
                break
            _play_subprocess(path)

    def stop(self) -> None:
        self._running = False
        try:
            self._path_queue.put_nowait(None)
        except queue.Full:
            pass
