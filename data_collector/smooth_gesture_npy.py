"""
제스처 npy 시퀀스에서 MediaPipe 인식 누락으로 인한 급격한 값 변화를 보정합니다.

- 손이 잠깐 사라질 때 해당 프레임이 0으로 채워지거나 값이 튀는 것을 감지하고,
  해당 프레임의 xyz(채널 0~2)를 이전/다음 정상 프레임 사이 선형 보간으로 교체합니다.
- 입력: (T, 21, C) 또는 (T, 42, C), C >= 3 (xyz 필수)
- 출력: 동일 shape, float32. 채널 0~2만 보정하며 나머지 채널은 유지.

사용 예:
  # 전체 Gesture 하위 모든 제스처 클래스 in-place 보정 (기본 input-dir이 data/Gesture)
  python smooth_gesture_npy.py --in-place

  # 특정 제스처만
  python smooth_gesture_npy.py --input-dir ./data/Gesture/Swipe_Left --output-dir ./data/Gesture_smoothed
  python smooth_gesture_npy.py --input-dir ./data/Gesture/Swipe_Left --in-place
  python smooth_gesture_npy.py --input-dir ./data/Gesture/Swipe_Left --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT_DIR = os.path.join(_SCRIPT_DIR, "data", "Gesture")

# 프레임 간 랜드마크 변화량이 이 값을 넘으면 해당 구간을 이상 프레임으로 간주
DEFAULT_DELTA_THRESHOLD = 0.05
# 손 전체 norm이 이 값 미만이면 "손 인식 누락"으로 간주 (정규화 좌표 0~1 기준)
ZERO_HAND_NORM_THRESHOLD = 0.1


def detect_outlier_frames(
    data: np.ndarray,
    delta_threshold: float,
    zero_norm_threshold: float,
) -> np.ndarray:
    """
    data: (T, L, C), C >= 3. xyz는 data[..., :3].
    Returns: (T,) bool, True = 정상 프레임, False = 이상 프레임(보간 대상).
    """
    T, L, C = data.shape
    xyz = data[:, :, :3].astype(np.float64)
    is_good = np.ones(T, dtype=bool)

    # 1) 프레임 간 최대 변화량 (각 프레임에서 "다음 프레임으로의 변화" 기준)
    if T > 1:
        diff = np.abs(np.diff(xyz, axis=0))
        # (T-1, L, 3) -> (T-1,) per transition
        max_delta_per_transition = diff.reshape(T - 1, -1).max(axis=1)
        # 프레임 i는 [i-1]->[i] 또는 [i]->[i+1] 중 하나라도 크면 이상
        for i in range(T):
            if i == 0:
                if max_delta_per_transition[0] > delta_threshold:
                    is_good[i] = False
            elif i == T - 1:
                if max_delta_per_transition[T - 2] > delta_threshold:
                    is_good[i] = False
            else:
                if (
                    max_delta_per_transition[i - 1] > delta_threshold
                    or max_delta_per_transition[i] > delta_threshold
                ):
                    is_good[i] = False

    # 2) 손 인식 누락: 한 손 전체가 거의 0인 경우 (42 랜드마크일 때만)
    if L >= 42:
        right = xyz[:, :21, :]
        left = xyz[:, 21:42, :]
        right_norm = np.linalg.norm(right, axis=(1, 2))
        left_norm = np.linalg.norm(left, axis=(1, 2))
        is_good &= right_norm >= zero_norm_threshold
        is_good &= left_norm >= zero_norm_threshold
    else:
        hand_norm = np.linalg.norm(xyz, axis=(1, 2))
        is_good &= hand_norm >= zero_norm_threshold

    return is_good


def interpolate_bad_frames(data: np.ndarray, is_good: np.ndarray) -> np.ndarray:
    """
    data: (T, L, C). is_good: (T,) bool.
    이상 프레임의 채널 0~2만 이전/다음 정상 프레임으로 선형 보간하여 교체.
    """
    out = np.array(data, dtype=np.float32, copy=True)
    T = data.shape[0]
    xyz = out[:, :, :3]

    good_indices = np.where(is_good)[0]
    if len(good_indices) == 0:
        return out  # 모두 이상이면 보간 불가, 원본 유지

    for i in range(T):
        if is_good[i]:
            continue
        # 이전/다음 정상 프레임
        prev_good = good_indices[good_indices <= i]
        next_good = good_indices[good_indices >= i]
        i_prev = int(prev_good[-1]) if len(prev_good) else None
        i_next = int(next_good[0]) if len(next_good) else None

        if i_prev is None and i_next is not None:
            xyz[i] = xyz[i_next]
        elif i_prev is not None and i_next is None:
            xyz[i] = xyz[i_prev]
        elif i_prev is not None and i_next is not None:
            if i_prev == i_next:
                xyz[i] = xyz[i_prev]
            else:
                t = (i - i_prev) / (i_next - i_prev)
                xyz[i] = (1.0 - t) * xyz[i_prev] + t * xyz[i_next]

    return out


def process_file(
    input_path: str,
    output_path: str,
    delta_threshold: float,
    zero_norm_threshold: float,
    dry_run: bool,
) -> tuple[bool, int]:
    """
    한 npy 파일 처리.
    Returns: (성공 여부, 보간된 이상 프레임 수)
    """
    try:
        data = np.load(input_path, allow_pickle=True)
    except Exception as e:
        print(f"  [skip] load error {input_path}: {e}", file=sys.stderr)
        return False, 0

    if data.ndim != 3 or data.shape[2] < 3 or data.shape[1] not in (21, 42):
        print(f"  [skip] unsupported shape {input_path}: {data.shape}", file=sys.stderr)
        return False, 0

    is_good = detect_outlier_frames(
        data, delta_threshold, zero_norm_threshold
    )
    n_bad = int((~is_good).sum())
    if n_bad == 0:
        if not dry_run:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            np.save(output_path, data.astype(np.float32))
        return True, 0

    smoothed = interpolate_bad_frames(data, is_good)
    if not dry_run:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.save(output_path, smoothed)
    return True, n_bad


def main():
    parser = argparse.ArgumentParser(
        description="제스처 npy: MediaPipe 인식 누락으로 튀는 프레임을 보간하여 부드럽게 보정",
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_INPUT_DIR,
        help=f"소스 디렉터리 (기본: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="결과 저장 디렉터리 (--in-place 미사용 시 지정)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="원본 파일 덮어쓰기",
    )
    parser.add_argument(
        "--delta-threshold",
        type=float,
        default=DEFAULT_DELTA_THRESHOLD,
        help=f"프레임 간 최대 변화량 임계값, 초과 시 이상 프레임 (기본: {DEFAULT_DELTA_THRESHOLD})",
    )
    parser.add_argument(
        "--zero-norm-threshold",
        type=float,
        default=ZERO_HAND_NORM_THRESHOLD,
        help="손 norm 하한, 미만이면 손 인식 누락 (기본: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 적용될 파일과 보간 프레임 수만 출력",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.in_place and not args.output_dir:
        print("--output-dir를 지정하거나 --in-place를 사용하세요.", file=sys.stderr)
        sys.exit(1)
    if args.in_place and args.output_dir:
        print("--output-dir와 --in-place는 동시에 사용할 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        print(f"입력 디렉터리가 없습니다: {input_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.abspath(args.output_dir) if args.output_dir else input_dir
    if not args.dry_run and not args.in_place:
        os.makedirs(output_dir, exist_ok=True)
    elif args.dry_run and not args.output_dir:
        output_dir = input_dir  # dry-run 시 출력 경로는 입력과 동일 구조로만 사용

    ok, skip, total_fixed = 0, 0, 0
    parent_name = os.path.basename(input_dir.rstrip(os.sep))

    # 단일 디렉터리(제스처별 폴더) 또는 제스처 루트(data/Gesture) 구조 모두 지원
    for name in sorted(os.listdir(input_dir)):
        path = os.path.join(input_dir, name)
        if os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                if not f.endswith(".npy"):
                    continue
                inp = os.path.join(path, f)
                out = os.path.join(output_dir, name, f)
                success, n_fixed = process_file(
                    inp, out,
                    args.delta_threshold,
                    args.zero_norm_threshold,
                    args.dry_run,
                )
                if success:
                    ok += 1
                    total_fixed += n_fixed
                    if n_fixed > 0 or args.dry_run:
                        print(f"  {'[would] ' if args.dry_run else ''}{name}/{f}: smoothed {n_fixed} frame(s)")
                else:
                    skip += 1
        elif name.endswith(".npy"):
            # 입력 디렉터리 바로 아래의 npy 파일 (예: data/Gesture/Swipe_Left/*.npy)
            inp = os.path.join(input_dir, name)
            # in-place면 같은 폴더에 덮어쓰기; 아니면 output_dir/제스처명/파일명 구조 유지
            out = os.path.join(output_dir, name) if args.in_place else os.path.join(output_dir, parent_name, name)
            success, n_fixed = process_file(
                inp, out,
                args.delta_threshold,
                args.zero_norm_threshold,
                args.dry_run,
            )
            if success:
                ok += 1
                total_fixed += n_fixed
                if n_fixed > 0 or args.dry_run:
                    print(f"  {'[would] ' if args.dry_run else ''}{parent_name}/{name}: smoothed {n_fixed} frame(s)")
            else:
                skip += 1

    print(f"처리: {ok}개, 스킵: {skip}개, 보간된 이상 프레임 총 {total_fixed}개" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
