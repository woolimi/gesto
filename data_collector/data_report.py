"""
data_collector/data/Gesture 아래 클래스별 .npy 데이터 개수 출력.
"""

import os

# 프로젝트 루트 기준: data_collector/data_report.py → data_collector/data/Gesture
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GESTURE_DATA_DIR = os.path.join(_SCRIPT_DIR, "data", "Gesture")


def main():
    if not os.path.isdir(GESTURE_DATA_DIR):
        print(f"경로가 없습니다: {GESTURE_DATA_DIR}")
        return

    counts = {}
    for name in sorted(os.listdir(GESTURE_DATA_DIR)):
        path = os.path.join(GESTURE_DATA_DIR, name)
        if not os.path.isdir(path):
            continue
        n = sum(1 for f in os.listdir(path) if f.endswith(".npy"))
        counts[name] = n

    if not counts:
        print("클래스/데이터가 없습니다.")
        return

    total = 0
    for cls, n in counts.items():
        print(f"  {cls}: {n}개")
        total += n
    print(f"  ---")
    print(f"  총계: {total}개")


if __name__ == "__main__":
    main()
