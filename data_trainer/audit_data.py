"""
데이터 검사 전용 스크립트. 학습 없이 데이터 양·형태·라벨 일관성만 점검합니다.
실행: python -m data_trainer.audit_data  또는  python data_trainer/audit_data.py
"""
import os
import numpy as np

# 프로젝트 루트 기준 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data_collector', 'data'))


def audit_legacy_data(data_dir):
    """데이터 양·형태·라벨 일관성 점검."""
    if not os.path.exists(data_dir):
        print(f"⚠️ 디렉토리 없음: {data_dir}")
        return
    modes = ["Gesture", "Posture"]
    per_class = {}
    issues = []
    for mode in modes:
        mode_path = os.path.join(data_dir, mode)
        if not os.path.exists(mode_path):
            continue
        for gesture in sorted(os.listdir(mode_path)):
            gpath = os.path.join(mode_path, gesture)
            if not os.path.isdir(gpath):
                continue
            npy_files = [f for f in os.listdir(gpath) if f.endswith(".npy")]
            per_class[gesture] = per_class.get(gesture, 0) + len(npy_files)
            if gesture != gesture.strip():
                issues.append(f"폴더명 앞뒤 공백: '{gesture}'")
            if gesture.lower() == gesture and gesture not in ("unknown",):
                issues.append(f"폴더명이 소문자만: '{gesture}' (대소문자 일치 권장: Pinch_In_Left, Swipe_Left 등)")
            if npy_files:
                try:
                    one = np.load(os.path.join(gpath, npy_files[0]))
                    if one.ndim != 3 or one.shape[1] != 21 or one.shape[2] != 3:
                        issues.append(f"{gesture}: 샘플 shape 기대 (T, 21, 3), 실제 {one.shape}")
                    if one.shape[0] < 5:
                        issues.append(f"{gesture}: 프레임 수 너무 적음 ({one.shape[0]})")
                except Exception as e:
                    issues.append(f"{gesture}: 로드 실패 - {e}")
    print("=" * 70)
    print("📊 데이터 검사 (audit)")
    print("=" * 70)
    for name, cnt in sorted(per_class.items()):
        print(f"   {name}: {cnt}개")
    print()
    if issues:
        print("⚠️ 발견된 이슈:")
        for i in issues:
            print(f"   - {i}")
        print()
    else:
        print("✅ shape/폴더명 이슈 없음.")
    print("💡 라벨은 '폴더 이름'으로만 결정됩니다. 수집 시 제스처 이름을 정확히 입력했는지 확인하세요.")
    print("   (예: Pinch_In_Left, Pinch_Out_Right, Swipe_Left, Swipe_Right)")
    print()


if __name__ == "__main__":
    audit_legacy_data(DATA_DIR)
