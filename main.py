"""
Gesto 메인 실행 파일 — 앱·카메라·모드·트리거·모드별 감지 연동.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap

import config
from app.main_window import MainWindow
from app.capture import CameraWorker
from app.mode_controller import ModeController
from app.recognition import TriggerWorker, ModeDetectionWorker
from app.workers import (
    play_trigger_start,
    play_trigger_stop,
    play_mode_sound,
    start_playback_worker,
    stop_playback_worker,
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    window = MainWindow()
    mode_controller = ModeController(initial_mode="GAME")
    camera = CameraWorker()
    trigger = TriggerWorker()
    mode_detection = ModeDetectionWorker(
        get_current_mode=mode_controller.get_mode,
        get_sensitivity=lambda: window.sensitivity,
    )

    # UI → Mode Controller
    window.mode_changed.connect(mode_controller.set_mode)
    window.mode_changed.connect(play_mode_sound)  # 모드 전환 시 해당 모드 효과음 재생
    mode_controller.set_mode(window.current_mode)
    # 시작/종료 버튼 클릭 → mode_controller 경유 (상태·UI·사운드 일원화)
    window.toggle_detection_requested.connect(
        lambda: mode_controller.set_detection_state(not mode_controller.get_is_detecting())
    )

    # 트리거 워커 → UI (손 랜드마크가 그려진 웹캠 표시)
    def on_frame_annotated(qimage):
        if not qimage.isNull():
            window.update_webcam_frame(QPixmap.fromImage(qimage))

    trigger.frame_annotated.connect(on_frame_annotated)

    # 카메라 → 공통 트리거 (모션 감지 시작/종료: 양손 펴기/주먹)
    camera.frame_bgr_ready.connect(trigger.enqueue_frame)

    # 카메라 → 모드별 감지 (모션 감지 중일 때만, 현재 모드에 해당하는 제스처/자세)
    def on_frame_bgr(frame_bgr):
        if mode_controller.get_is_detecting():
            mode_detection.enqueue_frame(frame_bgr)

    camera.frame_bgr_ready.connect(on_frame_bgr)

    # 트리거 → Mode Controller (모션 감지 시작/정지)
    trigger.trigger_start.connect(lambda: mode_controller.set_detection_state(True))
    trigger.trigger_stop.connect(lambda: mode_controller.set_detection_state(False))
    # Mode Controller → UI (감지 상태 반영)
    mode_controller.detection_state_changed.connect(window.set_detection_state)
    # Mode Controller → TriggerWorker (버튼으로 시작/종료 시 랜드마크 스타일 동기화)
    mode_controller.detection_state_changed.connect(trigger.set_motion_active)
    # 감지 시작/정지 시 효과음
    def on_detection_state_changed(is_active: bool):
        if is_active:
            play_trigger_start()
        else:
            play_trigger_stop()
    mode_controller.detection_state_changed.connect(on_detection_state_changed)

    # 모드별 감지 → Mode Controller (제스처 시 pynput 출력) + UI (인식된 제스처 표시)
    mode_detection.gesture_detected.connect(mode_controller.on_gesture)
    mode_detection.gesture_detected.connect(window.update_gesture)

    # 카메라 오류
    def on_camera_error(msg):
        window.statusBar().showMessage(msg)

    camera.error_occurred.connect(on_camera_error)

    start_playback_worker()
    camera.start()
    trigger.start()
    mode_detection.start()

    def on_quit():
        stop_playback_worker()
        camera.stop()
        trigger.stop()
        mode_detection.stop()
        camera.wait(3000)
        trigger.wait(3000)
        mode_detection.wait(3000)

    app.aboutToQuit.connect(on_quit)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
