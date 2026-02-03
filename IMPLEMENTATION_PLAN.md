# Gesto 구현 계획 (System Architecture 기반)

## 1. 문서 개요

- **제목**: Gesto 구현 계획 (System Architecture 기반)
- **목적**: 시스템 아키텍처에 맞춰 Mode Controller 중심의 실시간 인식 및 Pynput 제어를 구현한다.
- **참조**:
  - [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — 데이터 흐름, 레이어 역할, 폴더 매핑
  - [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md) — 시스템 요구사항
  - 폴더 구조: [app/](app/) (main_window, capture, mode_controller, recognition, workers, widgets, models, assets). Pynput 연동은 [app/mode_controller/](app/mode_controller/)에서 수행.

## 2. 시스템 아키텍처

- **상세 내용은 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) 참조.** (다이어그램, 레이어 역할, 폴더 매핑이 해당 문서에 정의됨.)
- **요약**: Mode Controller가 현재 모드에 따라 해당 모드 인식기를 선택하고, 인식 결과를 Pynput에 명령으로 전달한다. 이미지는 opencv에서 **바로 Mediapipe**로 전달하며, YOLO는 범위에서 제외한다.

## 3. 공통 LSTM 제스처 모델 (PPT / YouTube)

- **모델**: [data_trainer/models/lstm_legacy.tflite](data_trainer/models/lstm_legacy.tflite) — **한 가지 모델로 PPT·YouTube 둘 다 지원.**
- **제스처 클래스 (4종)**: `Pinch_In`, `Pinch_Out`, `Swipe_Left`, `Swipe_Right`
- **PPT 모드**: `Swipe_Left` / `Swipe_Right` 만 사용. **Pinch_In, Pinch_Out 은 무시** (다음/이전 슬라이드만 필요).
- **YouTube 모드**: 위 4가지 제스처 모두 사용 (10초 앞/뒤, 재생·정지, 음소거, 전체화면 등에 매핑).

## 4. 상세 요구사항 (DNT)

| DNT ID | Description | G & P | 동작 (제스처) |
|--------|-------------|-------|----------------|
| DNT-01 | 사용자는 데스크탑에서 프로그램을 실행/종료할 수 있다. | Gesture, Posture | 실행 : Hotkey, 종료 : Hotkey |
| DNT-02 | 사용자는 트리거 동작을 통해 모션인식의 시작과 종료를 제어 가능 | — | — |
| DNT-02-TRIG-01 | 트리거 동작 시작 모션을 하면 모션인식이 시작된다. | Gesture | 시작: 양손 펴기 |
| DNT-02-TRIG-02 | 트리거 동작 정지 모션을 하면 모션인식이 정지된다. | Gesture | 종료: 양 주먹 |
| DNT-03 | 사용자는 모션인식 시작과 종료를 확인 할 수 있어야 한다. | — | — |
| DNT-04 | 사용자는 자신의 모습을 볼 수 있어야 한다. | — | — |
| DNT-05 | 사용자는 자신이 선택한 모드를 볼 수 있어야 한다. | — | — |
| DNT-06 | 사용자는 각각의 모드를 동작으로 제어가 가능해야한다. | — | — |
| DNT-06-GME-01 | Game - 동작으로 직진이 가능해야한다. | Gesture | 검지만 위 방향으로 향할 시 |
| DNT-06-GME-02 | Game - 동작으로 후진이 가능해야한다. | Gesture | 검지만 아래 방향으로 향할 시 |
| DNT-06-GME-03 | Game - 동작으로 좌회전이 가능해야한다. | Gesture | 검지만 왼쪽 방향으로 향할 시 |
| DNT-06-GME-04 | Game - 동작으로 우회전이 가능해야한다. | Gesture | 검지만 오른쪽 방향으로 향할 시 |
| DNT-06-YTB-01 | Youtube - 동작으로 10초 빨리감기가 가능해야한다. | Gesture | **Swipe_Right** (공통 LSTM) |
| DNT-06-YTB-02 | Youtube - 동작으로 10초 뒤로감기가 가능해야한다. | Gesture | **Swipe_Left** (공통 LSTM) |
| DNT-06-YTB-03 | Youtube - 동작으로 재생이 가능해야한다. | Gesture | **Pinch_Out** 등 (공통 LSTM, YouTube 전용) |
| DNT-06-YTB-04 | Youtube - 동작으로 정지가 가능해야한다. | Gesture | **Pinch_Out** 등 (공통 LSTM, YouTube 전용) |
| DNT-06-YTB-05 | Youtube - 동작으로 음소거 토글이 가능해야한다. | Gesture | **Pinch_In** 등 (공통 LSTM, YouTube 전용) |
| DNT-06-YTB-06 | Youtube - 동작으로 전체화면 토글이 가능해야한다. | Gesture | **Pinch_In / Pinch_Out** 등 (공통 LSTM, YouTube 전용) |
| DNT-06-PPT-01 | PPT - 동작으로 다음 슬라이드로 이동해야한다. | Gesture | **Swipe_Right** (공통 LSTM, Pinch 무시) |
| DNT-06-PPT-02 | PPT - 동작으로 이전 슬라이드로 이동해야한다. | Gesture | **Swipe_Left** (공통 LSTM, Pinch 무시) |

## 5. Mode Controller 역할 (핵심)

- **입력**: UI에서의 모드 변경(`set_mode`)만. (YOLO/인물 영역은 현재 범위에서 제외.)
- **책임**:
  1. **현재 모드** 단일 소스로 유지.
  2. 실시간 루프에서 **현재 모드에 맞는 인식기**만 사용 (Game → Posture/검지 포인팅, PPT·YouTube → **공통 LSTM** `lstm_legacy.tflite`).
  3. PPT 모드에서는 LSTM 출력 중 **Swipe_Left / Swipe_Right 만 사용**하고, Pinch_In / Pinch_Out 은 무시.
  4. 인식 결과(제스처명)를 **명령**으로 변환하여 **Pynput**([app/mode_controller/](app/mode_controller/) 내)에 전달.
- **구현 방향**: [app/mode_controller/mode_controller.py](app/mode_controller/mode_controller.py)는 (1) 현재 모드·감지 on/off 단일 소스, (2) [app/recognition/registry.py](app/recognition/registry.py)로 현재 모드용 인식기 조회, (3) [app/workers/](app/workers/) 파이프라인과 연동해 인식 결과 → 제스처명(Pinch_In / Pinch_Out / Swipe_Left / Swipe_Right) → Pynput 키 입력을 오케스트레이션한다.

## 6. 구현 단계 (Phase) — 체크리스트

### Phase 1: Capture 및 PyQT UI

- [x] 웹캠(opencv) 확보 — [app/capture/camera.py](app/capture/camera.py) (QThread 사용)
- [x] UI에서 모드 선택·시작/종료·감도 표시 — [app/main_window.py](app/main_window.py), [app/widgets/gesture_display.py](app/widgets/gesture_display.py)
- [x] UI 이벤트가 Mode Controller에 모드 전달 (`set_mode(mode)` 수신)
- [x] S-04: 자신 모습 표시 (웹캠 영상)
- [x] S-05: 선택 모드 표시
- [x] S-02/S-02-TRIG-01/S-02-TRIG-02: 트리거 시작/종료 모션 (MediaPipe Posture: 양손 펴기=시작, 양손 주먹=정지)
- [x] S-03: 모션인식 시작·종료 확인

### Phase 2: Mode Controller 및 실시간 루프 오케스트레이션

- [x] "현재 모드 → 해당 모드 인식기 사용 → 인식 결과 → 명령 → Pynput" 실시간 루프 정립 ([main.py](main.py) 연동)
- [x] [app/mode_controller/mode_controller.py](app/mode_controller/mode_controller.py) — 감지 on/off, 제스처→Pynput 담당
- [x] [app/workers/mode_detection_worker.py](app/workers/mode_detection_worker.py)가 Mode Controller에서 현재 모드 읽기 (`get_current_mode`)
- [x] [app/recognition/registry.py](app/recognition/registry.py)로 해당 모드용 detector만 사용 (ppt/, youtube/, game/)
- [x] 모드 변경 시 Game/PPT/YouTube 중 해당 인식 경로만 사용

### Phase 3: MediaPipe + LSTM — 모드별 인식

- [x] **Game (Posture)**: [app/recognition/game/detector.py](app/recognition/game/detector.py) — 직진/후진/좌회전/우회전 (방향키, 양손·동시 2방향, 검지 포인팅)
- [ ] **PPT (공통 LSTM)**: [app/recognition/ppt/detector.py](app/recognition/ppt/detector.py) — **lstm_legacy.tflite** 사용. **Swipe_Left** → 이전 슬라이드, **Swipe_Right** → 다음 슬라이드. **Pinch_In / Pinch_Out 은 무시.**
- [ ] **YouTube (공통 LSTM)**: [app/recognition/youtube/detector.py](app/recognition/youtube/detector.py) — **lstm_legacy.tflite** 사용. Swipe_Left/Right → 10초 뒤/앞, Pinch_In/Out → 재생·정지·음소거·전체화면 등 (동일 모델, 4종 제스처 모두 사용)
- [ ] **공통 LSTM 인식기**: MediaPipe Hand Landmarker로 랜드마크 추출 → 시퀀스 버퍼 → lstm_legacy.tflite 추론 → Pinch_In / Pinch_Out / Swipe_Left / Swipe_Right 출력. PPT/YouTube 모드에서 공유, PPT는 Swipe만 사용
- [x] **공통**: 트리거(시작/종료) — [app/recognition/trigger.py](app/recognition/trigger.py), [app/workers/trigger_worker.py](app/workers/trigger_worker.py)
- [x] S-06-GME-01~04: Game 직진/후진/좌회전/우회전
- [ ] S-06-YTB-01~06: YouTube 제스처 (공통 LSTM 4종)
- [ ] S-06-PPT-01~02: PPT 다음/이전 슬라이드 (공통 LSTM, Swipe만)

### Phase 4: Pynput 연동 (명령 실행)

- [x] [app/mode_controller/mode_controller.py](app/mode_controller/mode_controller.py)에서 제스처명 → 키 매핑 후 Pynput으로 키 입력 실행 (`on_gesture`)
- [x] [app/workers/mode_detection_worker.py](app/workers/mode_detection_worker.py)의 `gesture_detected` 시그널이 Mode Controller `on_gesture`로 전달
- [ ] PPT/YouTube 제스처명 매핑: `Swipe_Left` / `Swipe_Right` / `Pinch_In` / `Pinch_Out` → [app/mode_controller/](app/mode_controller/) `_build_gesture_mapping`에 반영 (PPT는 Swipe만, YouTube는 4종)

### Phase 5: 통합 테스트 및 문서

- [ ] 통합 테스트: 모드 전환 → 해당 모드 인식만 동작 → Pynput 명령 실행 E2E
- [ ] README에 아키텍처·Mode Controller 역할 반영
- [ ] [GESTURE_GUIDE.md](GESTURE_GUIDE.md) 등 문서에 아키텍처·Mode Controller 역할 반영
