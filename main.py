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
    play_aot_on,
    play_aot_off,
    play_gesture_success,
    play_app_startup,
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    # Global Font Registration
    from PyQt6.QtGui import QFontDatabase
    import os
    font_path = os.path.join(config.ASSETS_DIR, "Giants-Inline.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)

    window = MainWindow()
    mode_controller = ModeController(initial_mode="PPT")
    camera = CameraWorker()
    trigger = TriggerWorker()
    mode_detection = ModeDetectionWorker(
        get_current_mode=mode_controller.get_mode,
        get_sensitivity=lambda: window.sensitivity,
    )

    # UI → Mode Controller
    window.mode_changed.connect(mode_controller.set_mode)
    window.mode_changed.connect(trigger.set_current_mode) # 트리거 워커에 모드 동기화
    window.mode_changed.connect(play_mode_sound)
    mode_controller.set_mode(window.current_mode)
    trigger.set_current_mode(window.current_mode)
    
    # 시작/종료 버튼 클릭 → mode_controller 경유
    window.toggle_detection_requested.connect(
        lambda: mode_controller.set_detection_state(not mode_controller.get_is_detecting())
    )

    # 카메라 → UI (랜드마크가 그려진 웹캠 표시)
    camera.frame_updated.connect(lambda qimg: window.update_webcam_frame(QPixmap.fromImage(qimg)))

    # 카메라 → 공통 트리거 (전달된 랜드마크로 시작/종료 제스처 확인)
    camera.landmarks_updated.connect(trigger.enqueue_landmarks)

    # 카메라 → 모드별 감지 (모션 감지 중일 때만 현재 모드 제스처 인식)
    def on_landmarks_extracted(landmarks, handedness):
        if mode_controller.get_is_detecting():
            mode_detection.enqueue_landmarks(landmarks, handedness)

    camera.landmarks_updated.connect(on_landmarks_extracted)

    # 트리거 → Mode Controller (모션 감지 시작/정지)
    trigger.trigger_start.connect(lambda: mode_controller.set_detection_state(True))
    trigger.trigger_stop.connect(lambda: mode_controller.set_detection_state(False))

    # 트리거 → Always on Top 제어
    trigger.trigger_aot_on.connect(lambda: window.set_always_on_top(True))
    trigger.trigger_aot_off.connect(lambda: window.set_always_on_top(False))
    
    # 트리거 → Always on Top 사운드
    trigger.trigger_aot_on.connect(play_aot_on)
    trigger.trigger_aot_off.connect(play_aot_off)

    # Mode Controller → UI (감지 상태 반영)
    mode_controller.detection_state_changed.connect(window.set_detection_state)

    # Mode Controller → TriggerWorker & Camera (랜드마크 렌더링 상태 동기화)
    mode_controller.detection_state_changed.connect(trigger.set_motion_active)
    mode_controller.detection_state_changed.connect(camera.set_motion_active)

    # 감지 시작/정지 시 효과음
    def on_detection_state_changed(is_active: bool):
        if is_active:
            play_trigger_start()
        else:
            play_trigger_stop()
    mode_controller.detection_state_changed.connect(on_detection_state_changed)

    # 모드별 감지 → Mode Controller + UI
    mode_detection.gesture_detected.connect(mode_controller.on_gesture)
    mode_detection.gesture_detected.connect(window.update_gesture)
    if config.GESTURE_DEBUG:
        mode_detection.gesture_debug_updated.connect(window.update_gesture_debug)

    # 제스처 인식 성공 시 효과음
    last_played_gesture = [None]
    def on_gesture_detected(gesture, confidence, cooldown_until):
        if not gesture:
            last_played_gesture[0] = None
            return
        if gesture != last_played_gesture[0]:
            if window.current_mode != "GAME":
                play_gesture_success()
            last_played_gesture[0] = gesture

    mode_detection.gesture_detected.connect(on_gesture_detected)

    # 카메라 오류
    camera.error_occurred.connect(lambda msg: window.statusBar().showMessage(msg))

    # 카메라 소스 변경 핸들러
    def on_camera_source_changed(new_index):
        if config.CAMERA_INDEX == new_index:
            return
            
        print(f"Switching camera to index: {new_index}")
        camera.stop()
        camera.wait(2000) # Wait for thread to finish
        config.CAMERA_INDEX = new_index
        camera.start()
        
    window.camera_source_changed.connect(on_camera_source_changed)

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
    play_app_startup()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
