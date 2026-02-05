"""
제스처 npy 시퀀스: 뒷 N프레임 제거 후 앞쪽만 시간축으로 늘려 30프레임으로 리샘플.

- 입력: (30, 21, 3) 또는 (30, 42, 3)
- 처리: 마지막 cut_frames 제거 → 26프레임, 비선형 매핑으로 앞 구간만 강조 후 30프레임 보간
- 출력: (30, 21, 3) 또는 (30, 42, 3), float32

사용 예:
  python resample_gesture_frames.py --output-dir ./data/Gesture_resampled
  python resample_gesture_frames.py --in-place --dry-run
"""

import argparse
import os
import sys

import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT_DIR = os.path.join(_SCRIPT_DIR, "data", "Gesture")

TARGET_FRAMES = 30


def time_warp_resample(data: np.ndarray, cut_frames: int, alpha: float) -> np.ndarray:
    """
    data: (T, L, 3), T==30. 마지막 cut_frames 제거 후 앞쪽만 늘려 30프레임 리샘플.
    alpha > 1 이면 초반에 더 많은 출력 프레임 배정 (앞만 늘림, 중간/뒤는 선형에 가깝게).
    """
    T, L, C = data.shape
    if T != TARGET_FRAMES:
        raise ValueError(f"Expected {TARGET_FRAMES} frames, got {T}")
    keep = T - cut_frames  # 26
    trimmed = data[:keep].astype(np.float32)  # (26, L, 3)

    # 출력 인덱스 i (0..29) → 입력 시간 t (0..keep-1)
    # alpha > 1: (i/29)^alpha 가 작은 i에서 작음 → 앞 구간에 많은 출력 프레임 배정
    out = np.zeros((TARGET_FRAMES, L, C), dtype=np.float32)
    last_idx = keep - 1
    for i in range(TARGET_FRAMES):
        if TARGET_FRAMES == 1:
            t = 0.0
        else:
            t = last_idx * (i / (TARGET_FRAMES - 1)) ** alpha
        t = min(t, last_idx)
        lo = int(np.floor(t))
        hi = min(int(np.ceil(t)), last_idx)
        s = t - lo
        if lo == hi:
            out[i] = trimmed[lo]
        else:
            out[i] = (1 - s) * trimmed[lo] + s * trimmed[hi]
    return out


def process_file(
    input_path: str,
    output_path: str,
    cut_frames: int,
    alpha: float,
    dry_run: bool,
) -> bool:
    """한 npy 파일 처리. 성공 시 True, 스킵/실패 시 False."""
    try:
        data = np.load(input_path, allow_pickle=True)
    except Exception as e:
        print(f"  [skip] load error {input_path}: {e}", file=sys.stderr)
        return False

    if data.ndim != 3 or data.shape[2] != 3 or data.shape[1] not in (21, 42):
        print(f"  [skip] unsupported shape {input_path}: {data.shape}", file=sys.stderr)
        return False

    if data.shape[0] != TARGET_FRAMES:
        print(f"  [skip] not {TARGET_FRAMES} frames {input_path}: {data.shape[0]}", file=sys.stderr)
        return False

    resampled = time_warp_resample(data, cut_frames=cut_frames, alpha=alpha)
    if not dry_run:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.save(output_path, resampled)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="제스처 npy: 뒷 N프레임 제거 후 앞/중간 늘려 30프레임으로 리샘플",
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_INPUT_DIR,
        help=f"소스 루트 (기본: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="결과 저장 루트 (--in-place 미사용 시 지정 필요)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="원본 파일 덮어쓰기",
    )
    parser.add_argument(
        "--cut-frames",
        type=int,
        default=4,
        help="제거할 뒷프레임 수 (기본: 4)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.8,
        dest="alpha",
        help="앞쪽 스트레치 강도, 1 초과 권장 (기본: 1.8, 클수록 앞 구간만 더 늘어남)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 적용될 파일만 출력",
    )
    args = parser.parse_args()

    if not args.in_place and not args.output_dir:
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
    if not args.dry_run and not args.in_place and not os.path.isdir(os.path.dirname(output_dir)):
        os.makedirs(os.path.dirname(output_dir) or ".", exist_ok=True)

    ok, skip = 0, 0
    for name in sorted(os.listdir(input_dir)):
        path = os.path.join(input_dir, name)
        if not os.path.isdir(path):
            continue
        for f in sorted(os.listdir(path)):
            if not f.endswith(".npy"):
                continue
            inp = os.path.join(path, f)
            out = os.path.join(output_dir, name, f)
            if process_file(inp, out, args.cut_frames, args.alpha, args.dry_run):
                ok += 1
                if args.dry_run:
                    print(f"  [would process] {name}/{f}")
            else:
                skip += 1

    print(f"처리: {ok}개, 스킵: {skip}개" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
