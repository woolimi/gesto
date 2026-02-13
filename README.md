<div align="center">
  <img src="app/assets/gesto-light.png" alt="Gesto Logo" width="200"/>
</div>

# Gesto: Deep Learning-based Hand Gesture Recognition & PC Control System

## 1. Overview

> **Gesto**는 웹캠 하나만으로 사용자의 손동작을 정밀하게 인식하여 일상적인 PC 환경을 제어하는 프레임워크입니다. 신체적 제약이나 요리/작업 중 하드웨어 조작이 어려운 상황에서 손을 대지 않고도 자유로운 인터페이스를 제공하는 것을 목적으로 합니다. 

* **프로젝트명**: Gesto
* **프로젝트 배경**: 환경적/신체적 제약으로 인한 하드웨어 상호작용(터치, 키보드)의 불가능한 상황 해결 
* **타겟 사용자**: PPT 발표자, YouTube 시청자, 웹캠 기반 게임 사용자 등 원격 제어가 필요한 모든 사용자 
* **핵심 기술**: 
	* MediaPipe: 랜드마크 추출
	* LSTM: 시계열 데이터 학습
	* Python 

## 2. Features

* **시스템 및 트리거 제어**: 특정 제스처를 통해 인식 기능을 활성화/비활성화하여 오작동을 방지합니다.
* **멀티 모드 지원**: 게임, YouTube, PPT 등 각 어플리케이션에 최적화된 모드별 동작을 수행합니다.
	* **게임**: 4방향(전/후/좌/우) 이동 제어.
	* **YouTube**: 재생/일시정지, 볼륨 조절, 10초 앞/뒤 이동, 전체화면 토글.
	* **PPT**: 슬라이드 이전/다음 이동, 전체화면/최소화.
* **실시간 모니터링 UI**: 현재 활성화된 모드와 카메라 피드를 실시간으로 확인하며 상태 알림을 피드백합니다.
* **고성능 데이터 정제**: 선형 보간법(Linear Interpolation) 및 11채널 피처 엔지니어링을 통해 인식률을 극대화했습니다.

## 3. Demo

*(추후에 실제 시연 첨부)*

* **System Architecture**: 지연 시간(Latency) 최소화를 위해 `Camera Input → Main Process → Action Output`의 단방향 파이프라인 구조를 채택했습니다.
* **Performance Improvement**: 초기 모델 대비 비약적인 성능 향상을 기록했으며, 특히 'Swipe Left'의 경우 96% 이상의 F1-Score를 달성했습니다.

## 4. Tech Stack

* **AI Model**: LSTM (Long Short-Term Memory) 
* **Hand Tracking**: MediaPipe Solution 
* **Language**: Python
* **Libraries**: NumPy (데이터 저장/경량화), OpenCV, PyQt (GUI) 
* **Architecture Pattern**: Observer Pattern, Composition Root 

## 5. Installation

본 프로젝트는 단일 어플리케이션으로 로컬 환경에서 실행됩니다.

```bash
git clone git@github.com:addinedu-physicalai-1st/deeplearning-repo-4.git
conda create -n gesto python=3.10
conda activate gesto
pip install -r requirements.txt
python main.py
```

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

## 6. Project Structure

객체 지향 설계와 독립적인 멀티쓰레드 모듈 구성을 통해 결합도를 낮췄습니다.

```md
app/
├── main_window.py              # 사용자 인터페이스
├── capture/                    # 실시간 영상 입력 및 랜드마크 추출
├── mode_controller/            # 시스템 상태 및 모드 관리, pynput 하드웨어 제어
├── recognition/                # 인식 (trigger, registry, ppt/youtube/game)
├── workers/                    # QThread (트리거·모드감지·효과음)
├── widgets/                    # PyQt6 위젯
├── models/                     # 학습된 LSTM 모델
└── assets/                     # 이미지·오디오

config.py
main.py
```

## 7. Performance Evaluation

| Gesture     | 초기 F1-Score | 최종 F1-Score |
| ----------- | ----------- | ----------- |
| Pinch In    | 0.5231      | **0.8358**  |
| Pinch Out   | 0.0040      | **0.6774**  |
| Swipe Left  | 0.6245      | **0.9655**  |
| Swipe Right | 0.00        | **0.7234**  |

단순 좌표값(3채널)에서 속도, 가속도, 기하학적 특징을 추가한 **11채널 확장**을 통해 정확도를 대폭 향상시켰습니다.

