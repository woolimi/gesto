"""
Flip (left-right mirror) all .npy samples for a specific gesture under:
  data_collector/data/Gesture/<gesture_name>/

This script is intended for MediaPipe Hands landmark datasets collected by
`data_collector/collect_mp.py`.

Supported array shapes:
- (T, 42, 3): two hands concatenated as [Right(21), Left(21)].
  - Mirror x coordinate: x -> 1 - x
  - Swap hand slots (Right <-> Left) after mirroring, because handedness flips.
- (T, 21, 3): single-hand samples (mirror x only).
- (T, 126): flattened version of (T, 42, 3) (will be reshaped and restored).
- (T, 63): flattened version of (T, 21, 3) (will be reshaped and restored).

Default behavior does NOT overwrite originals:
- If --output-gesture is provided, files are written to that gesture folder.
- Otherwise files are written next to originals with a suffix.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Tuple

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT_DIR / "data_collector" / "data"


def _flip_sample(arr: np.ndarray) -> np.ndarray:
    """
    Apply left-right mirror to a single sample array.
    Returns a new array (does not modify input in-place).
    """
    a = np.array(arr, copy=True)

    if a.ndim != 2 and a.ndim != 3:
        raise ValueError(f"Unsupported ndim={a.ndim}; expected 2 or 3. shape={a.shape}")

    # Flattened shapes: (T, 126) or (T, 63)
    if a.ndim == 2:
        t, d = a.shape
        if d == 126:
            a3 = a.reshape(t, 42, 3)
            flipped = _flip_sample(a3)
            return flipped.reshape(t, 126)
        if d == 63:
            a3 = a.reshape(t, 21, 3)
            flipped = _flip_sample(a3)
            return flipped.reshape(t, 63)
        raise ValueError(f"Unsupported 2D shape={a.shape}; expected (T,126) or (T,63).")

    # Landmark shapes: (T, N, 3)
    if a.shape[-1] != 3:
        raise ValueError(f"Unsupported last-dim={a.shape[-1]}; expected 3. shape={a.shape}")

    t, n, _ = a.shape
    # Mirror x in normalized image space.
    a[:, :, 0] = 1.0 - a[:, :, 0]

    if n == 42:
        # Right(0:21) <-> Left(21:42)
        right = a[:, 0:21, :].copy()
        left = a[:, 21:42, :].copy()
        a[:, 0:21, :] = left
        a[:, 21:42, :] = right
        return a

    if n == 21:
        return a

    raise ValueError(f"Unsupported landmark count n={n}; expected 21 or 42. shape={a.shape}")


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
    parser = argparse.ArgumentParser(description="Flip (mirror) gesture .npy samples left-right.")
    parser.add_argument("--gesture", required=True, help="Input gesture folder name (e.g., Swipe_Left).")
    parser.add_argument(
        "--output-gesture",
        default=None,
        help="Output gesture folder name. If omitted, writes to same folder (with filename suffix) unless --overwrite is set.",
    )
    parser.add_argument(
        "--mode",
        default="Gesture",
        choices=["Gesture", "Posture"],
        help="Dataset mode directory under data_collector/data/.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Base data dir (default: <repo>/data_collector/data).",
    )
    parser.add_argument(
        "--suffix",
        default="_flipped",
        help="Filename suffix when not overwriting and output-gesture is not changing folders.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite original files in-place (dangerous). Ignored if --output-gesture is set to a different folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print planned operations; do not write any files.",
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
        flipped = _flip_sample(arr)

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
        np.save(dst, flipped.astype(np.float32, copy=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

