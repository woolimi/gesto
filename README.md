
# Gesto

![ppt 모드](https://images.prismic.io/woolimi/aaUlj8FoBIGEg9yq_ppt-mode.gif?auto=format,compress)


## Overview

Gesto 는 카메라로 손의 제스처를 인식해서 PPT, Youtube 를 제어하는 프로그램입니다. Mediapipe 를 사용하여 손 관절을 판단하고, LSTM 모델을 사용하여 제스처를 인식한 뒤에 PyAutoGUI 를 사용하여 제스처에 맵핑된 키보드 키를 트리거 합니다. 발표를 해야하는데 ppt 리모컨을 깜박하고 가져오지 않았을 때, 과자를 먹으며 유튜브를 보는데 키보드에 손을 대기 싫을 때 사용해보세요.


## How to start

```bash
uv sync
uv run python main.py
```

## Features

* 동작인식 시작: 양 손바닥을 화면에 보여주기
* 동작인식 종료: 양 주먹을 화면에 모여주기
* PPT 모드
	![ppt 모드](https://images.prismic.io/woolimi/aaUlj8FoBIGEg9yq_ppt-mode.gif?auto=format,compress)
	- 다음 슬라이드: Swipe Left (왼손은 주먹, 오른손은 왼쪽으로 스와이프)
	- 이전 슬라이드: Swipe Right (오른손은 주먹, 왼손은 오른쪽으로 스와이프)
	- 최소화: Pinch In (한손은 주먹, 다른 손은 pinch in) 
	- 최대화: Pinch Out (한손은 주먹, 다른 손은 pinch out)

	
* Youtube 모드
	![youtube 모드](https://images.prismic.io/woolimi/aaUlkMFoBIGEg9yr_youtube-mode.gif?auto=format,compress)
	- 앞으로 5초: Swipe Left (왼손은 주먹, 오른손은 왼쪽으로 스와이프)
	- 뒤로 5초: Swipe Right (오른손은 주먹, 왼손은 오른쪽으로 스와이프)
	- 최소화: Pinch In (한손은 주먹, 다른 손은 pinch in) 
	- 최대화: Pinch Out (한손은 주먹, 다른 손은 pinch out)
	- 시작: Play (한손은 주먹, 다른손은 클릭하듯이)
	- 정지: Pause (시작과 동일)

## Tech Stack

* **AI Model**: LSTM (Long Short-Term Memory) 
* **Hand Tracking**: MediaPipe Solution 
* **Language**: Python
* **Libraries**: NumPy (데이터 저장/경량화), OpenCV, PyQt (GUI) 
* **Architecture Pattern**: Observer Pattern, Composition Root 

### Hugginface data 가져오기

```bash
# git xet 설치가 안되있으면 설치
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/huggingface/xet-core/refs/heads/main/git_xet/install.sh | sh

# lfs 설치
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs

# 폴더로 이동
cd data_collector
# 데이터 가져오기
git clone git@hf.co:datasets/dnt-addinedu/data
```

## Project Structure

```md
app/
├── main_window.py              # 사용자 인터페이스
├── capture/                    # 실시간 영상 입력 및 랜드마크 추출 (camera)
├── mode_controller/            # 시스템 상태 및 모드 관리, pynput 하드웨어 제어
├── recognition/                # 제스처 인식
│   ├── trigger.py, registry.py, lstm_gesture_base.py
│   ├── ppt/                    # PPT 모드 감지
│   ├── youtube/                # Youtube 모드 감지
│   └── game/                   # 게임 모드 감지
├── workers/                    # QThread (트리거·모드감지·효과음)
├── widgets/                    # PyQt6 위젯 (webcam_panel, control_panel, gesture_display 등)
└── models/                     # 학습된 LSTM 모델·라벨

lib/                            # 손 특징 추출 등 공용 유틸 (hand_features)
data_collector/                 # 제스처 데이터 수집·전처리
data_trainer/                   # LSTM 학습 (train, audit_data, analyze_video)
validation/                     # 데이터·추론 검증 스크립트

config.py
main.py
```

## 발표영상

[말 한마디 없이 손짓으로 컴퓨터 제어하기 👋 (MediaPipe + LSTM 제스처 인식)](https://www.youtube.com/watch?v=nKU_hdknbqM)

## Contributors

* [송민규](https://github.com/ned-razzz)
* [최민성](https://github.com/Minssuung)
* [이정우](https://github.com/joey114132)
* [박우림](https://github.com/woolimi)
