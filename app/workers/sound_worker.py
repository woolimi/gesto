"""
효과음 재생 워커 — QThread에서 MP3 재생. 재생 로직·워커·API 통합.
"""

import os
import time as _time
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
_last_play_time: float = 0.0


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
    _enqueue_play(config.ASSETS_DIR, "motion-trigger.wav", volume=0.7)


def play_trigger_stop() -> None:
    """모션 감지 종료 효과음 재생."""
    _enqueue_play(config.ASSETS_DIR, "motion-trigger.wav", volume=0.6)


def play_mode_sound(mode: str) -> None:
    """모드 전환 시 효과음 재생."""
    _enqueue_play(config.ASSETS_DIR, "mode-switch.wav", volume=0.8)


def play_aot_on() -> None:
    """항상 위에 고정 시 효과음."""
    _enqueue_play(config.ASSETS_DIR, "aot-toggle.wav", volume=0.7)


def play_aot_off() -> None:
    """항상 위에 고정 해제 시 효과음."""
    _enqueue_play(config.ASSETS_DIR, "aot-toggle.wav", volume=0.6)


def play_gesture_success() -> None:
    """제스처 인식 성공 효과음."""
    _enqueue_play(config.ASSETS_DIR, "gesture-success.wav", volume=0.6)


def play_ui_click() -> None:
    """UI 버튼 클릭 효과음."""
    _enqueue_play(config.ASSETS_DIR, "ui-click.wav", volume=1.0)


def play_app_startup() -> None:
    """앱 시작 시 오프닝 효과음."""
    _enqueue_play(config.ASSETS_DIR, "gesture-success.wav", volume=0.8)


def _enqueue_play(assets_dir: str, filename: str, volume: float = 1.0) -> None:
    global _last_play_time
    path = os.path.join(assets_dir, filename)
    if not os.path.isfile(path):
        return
        
    # 동일한 사운드가 너무 짧은 간격으로 재생되는 것을 방지 (0.2초 쿨다운)
    current_time = _time.time()
    if current_time - _last_play_time < 0.2:
        return
    _last_play_time = current_time

    if _worker is not None:
        _worker.enqueue(path, volume)
    else:
        _play_mp3(path, volume)


def _play_mp3(path: str, volume: float = 1.0) -> None:
    if not os.path.isfile(path):
        return
    if _Player is not None and _AudioOutput is not None and _QUrl is not None:
        # Linux에서 .wav 파일은 aplay가 더 안정적인 경우가 많음
        if sys.platform == "linux" and path.endswith(".wav") and shutil.which("aplay"):
            _play_subprocess(path, volume)
        else:
            _play_qt(path, volume)
    else:
        _play_subprocess(path, volume)




def _play_qt(path: str, volume: float = 1.0) -> None:
    try:
        player = _Player()
        audio_output = _AudioOutput()
        audio_output.setVolume(volume)
        player.setAudioOutput(audio_output)
        player.setSource(_QUrl.fromLocalFile(path))
        player.play()
        
        # Keep both alive
        _players.append((player, audio_output))

        def _cleanup():
            try:
                for p, a in _players[:]:
                    if p == player:
                        _players.remove((p, a))
                        break
            except ValueError:
                pass

        player.mediaStatusChanged.connect(
            lambda s: _cleanup() if s == _Player.MediaStatus.EndOfMedia else None
        )
    except Exception:
        _play_subprocess(path)


def _play_subprocess(path: str, volume: float = 1.0) -> None:
    """시스템 플레이어 (macOS afplay, Ubuntu ffplay 등)."""
    cmd: Optional[list[str]] = None
    if sys.platform == "darwin":
        if shutil.which("afplay"):
            # afplay volume is 0 to 255ish but 1.0 is standard
            cmd = ["afplay", "-v", str(volume), path]
    elif sys.platform == "linux":
        if shutil.which("ffplay"):
            # ffplay volume is 0 to 100
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(volume * 100)), path]
        elif shutil.which("aplay") and path.endswith(".wav"):
            cmd = ["aplay", "-q", path] # aplay doesn't have easy volume flag
        elif shutil.which("mpg123"):
            cmd = ["mpg123", "-q", "-f", str(int(volume * 32768)), path]
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
        self._path_queue: queue.Queue[Optional[tuple[str, float]]] = queue.Queue(maxsize=32)
        self._running = True

    def enqueue(self, path: str, volume: float = 1.0) -> None:
        try:
            self._path_queue.put_nowait((path, volume))
        except queue.Full:
            pass

    def run(self) -> None:
        while self._running:
            try:
                item = self._path_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                break
            path, volume = item
            _play_mp3(path, volume)

    def stop(self) -> None:
        self._running = False
        try:
            self._path_queue.put_nowait(None)
        except queue.Full:
            pass
