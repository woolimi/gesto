# Gesto 프로젝트 규칙

## 프로젝트 개요

Gesto는 웹캠과 제스처만으로 PPT와 유투브를 제어하는 핸즈프리 발표 도구입니다.

## 기술 스택

- **Python**: 3.10
- **Mediapipe**: 0.10.32 (Task API 사용 필수)
  - Mediapipe 0.10.x 버전부터는 Task API를 사용해야 함
  - `mp.tasks.vision.HandLandmarker` 사용
  - 구식 `mp.solutions.hands` API는 사용 불가
- **LSTM**: 제스처 시퀀스 학습 및 분류
- **PyAutoGui**: 화면 제어 및 자동화
- **PyQT6**: GUI 애플리케이션

## 개발 환경

- **가상환경**: conda 환경 사용
  ```bash
  conda create -n gesto python=3.10
  conda activate gesto
  ```

## 프로젝트 구조 가이드

프로젝트는 다음과 같은 구조를 권장합니다:

```
gesto/
├── app/                    # 애플리케이션 코드
│   ├── capture/           # 웹캠 캡처
│   ├── mode_controller/   # 모드 컨트롤
│   ├── recognition/       # 인식 (Posture 트리거 등)
│   ├── widgets/           # PyQT6 위젯
│   ├── models/            # Hand Landmarker 등 모델
│   ├── assets/            # 이미지·오디오 리소스
│   └── data/              # 데이터
├── config.py
├── main.py
└── tests/                 # 테스트 코드
```

## 코딩 컨벤션

### Python 스타일

- **코드 스타일**: PEP 8 준수
- **타입 힌팅**: 가능한 경우 타입 힌팅 사용
- **문서화**: 모든 함수와 클래스에 docstring 작성
- **네이밍**:
  - 클래스: PascalCase (예: `GestureRecognizer`)
  - 함수/변수: snake_case (예: `detect_gesture`)
  - 상수: UPPER_SNAKE_CASE (예: `MAX_GESTURE_DURATION`)

### 모듈 구조

- 각 기능별로 모듈 분리
- 순환 참조 방지
- 명확한 인터페이스 정의

## 기능 구현 가이드

### 1. 공통필수기능

- **동작 감지 시작**: 웹캠 활성화 및 제스처 인식 시작
- **동작 감지 종료**: 웹캠 비활성화 및 리소스 정리

### 2. PPT 전용 기능

- **다음 슬라이드**: 키보드 단축키 또는 PyAutoGui로 제어
- **이전 슬라이드**: 키보드 단축키 또는 PyAutoGui로 제어
- **슬라이드 쇼 시작**: PowerPoint 자동화

### 3. 유투브 모드 기능

- **재생/일시정지**: 스페이스바 또는 클릭 제어
- **볼륨업/볼륨다운**: 키보드 단축키 제어
- **음소거**: 키보드 단축키 제어
- **전체화면**: F 키 또는 더블클릭 제어

## 제스처 인식 구현

### Mediapipe 사용

- **버전**: 0.10.32
- **API**: Task API 사용 필수 (`mp.tasks.vision.HandLandmarker`)
- Mediapipe Hands 솔루션을 사용하여 손 랜드마크 추출
- 실시간 처리 성능 고려
- 제스처 인식 정확도 최적화
- **주의**: 구식 `mp.solutions.hands` API는 0.10.x 버전에서 사용 불가

### LSTM 모델

- 시퀀스 데이터를 입력으로 받는 LSTM 모델 사용
- 제스처 시퀀스 학습 및 분류
- 모델 파일은 `app/models/` 디렉토리에 저장

## UI 구현 (PyQT6)

- 모던하고 직관적인 UI 디자인
- 실시간 제스처 인식 상태 표시
- 모드 전환 (PPT/유투브) 기능
- 설정 및 캘리브레이션 옵션

## 에러 처리

- 웹캠 접근 실패 시 명확한 에러 메시지
- 제스처 인식 실패 시 재시도 로직
- 예외 상황에 대한 적절한 로깅

## 성능 고려사항

- 실시간 제스처 인식 성능 최적화
- 웹캠 프레임 처리 지연 최소화
- 메모리 사용량 관리

## 테스트

- 각 모듈별 단위 테스트 작성
- 제스처 인식 정확도 테스트
- 통합 테스트 시나리오 작성

## 주의사항

- 웹캠 권한 요청 처리
- 크로스 플랫폼 호환성 고려 (Windows, macOS, Linux)
- PyAutoGui 사용 시 화면 해상도 고려
- 제스처 인식 민감도 조절 기능 제공
