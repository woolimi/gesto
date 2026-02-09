"""
동작 데이터(.npy)의 프레임 순서를 역순(Time-reverse)으로 뒤집습니다.
입력 경로: data_collector/data/Gesture/<gesture_name>/

지원하는 배열 형태:
- (T, N, 3): T(시간) 축을 기준으로 프레임 순서를 뒤집음.
- (T, D): flattened 형태에서도 동일하게 시간축 반전 적용.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Tuple

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT_DIR / "data_collector" / "data"


def _reverse_sample(arr: np.ndarray) -> np.ndarray:
    """
    샘플 배열의 시간축(axis 0)을 역순으로 뒤집습니다.
    """
    # np.flip(arr, axis=0)을 사용하여 첫 번째 차원(T)을 반전시킵니다.
    # copy()를 사용하여 메모리 연속성을 보장합니다.
    return np.flip(arr, axis=0).copy()


def _resolve_paths(
    data_dir: Path,
    mode: str,
    input_gesture: str,
    output_gesture: str | None,
) -> Tuple[Path, Path]:
    base = data_dir / mode
    in_dir = base / input_gesture
    out_dir = base / (output_gesture if output_gesture else input_gesture)
    return in_dir, out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Reverse gesture .npy samples in time (T-axis).")
    parser.add_argument("--gesture", required=True, help="Input gesture folder name (e.g., Swipe_Up).")
    parser.add_argument(
        "--output-gesture",
        default=None,
        help="Output gesture folder name. If omitted, writes to same folder with suffix.",
    )
    parser.add_argument(
        "--mode",
        default="Gesture",
        choices=["Gesture", "Posture"],
        help="Dataset mode directory.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Base data dir.",
    )
    parser.add_argument(
        "--suffix",
        default="_reversed",
        help="Filename suffix when not overwriting.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite original files in-place.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print planned operations.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    in_dir, out_dir = _resolve_paths(data_dir, args.mode, args.gesture, args.output_gesture)

    if not in_dir.is_dir():
        raise SystemExit(f"Input dir not found: {in_dir}")

    npy_files = sorted(in_dir.glob("*.npy"))
    if not npy_files:
        print(f"No .npy files found in: {in_dir}")
        return 0

    # Decide write strategy.
    output_changes_folder = args.output_gesture is not None and out_dir != in_dir
    do_overwrite = bool(args.overwrite) and not output_changes_folder
    if do_overwrite:
        out_dir = in_dir

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input : {in_dir}")
    print(f"Output: {out_dir} ({'overwrite' if do_overwrite else 'copy'})")
    print(f"Files : {len(npy_files)}")

    for src in npy_files:
        arr = np.load(src)
        
        # 시간축 반전 수행
        reversed_arr = _reverse_sample(arr)

        if do_overwrite:
            dst = src
        else:
            if output_changes_folder:
                dst = out_dir / src.name
            else:
                dst = out_dir / f"{src.stem}{args.suffix}{src.suffix}"

        print(f"- {src.name} -> {dst.name}  shape={arr.shape}")
        if args.dry_run:
            continue
        np.save(dst, reversed_arr.astype(np.float32, copy=False))

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        raise SystemExit(exit_code)
    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)