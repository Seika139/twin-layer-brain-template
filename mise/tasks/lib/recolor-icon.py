"""PNG の特定色領域だけを新しい accent color に差し替える (in-place)。

scaffold-brain が chrome-extension/icon{48,128}.png を brain ごとの accent
color に塗り直すために使う。対象はテンプレ PNG のティール面 (hue ~180°,
sat>=0.3) のみで、白文字 (sat=0)、黒輪郭 (value=0)、透明背景は触らない。

Hue だけを差し替え、Saturation / Value / Alpha は画素ごとに保持する。
これにより元の anti-alias のエッジ階調が新色でもそのまま再現される。

使い方:
    uv run --with pillow python mise/tasks/lib/recolor-icon.py \
        --target '#7b1fa2' \
        chrome-extension/icon48.png chrome-extension/icon128.png
"""

from __future__ import annotations

import argparse
import colorsys
import random
import sys
from pathlib import Path

from PIL import Image

_RECOLOR_ICON_TEXT = "\033[38;5;51m[recolor-icon]\033[0m"


def hex_to_hue_deg(value: str) -> float:
    """'#RRGGBB' から HSV の Hue (0-360°) だけを抜き出す。"""
    s = value.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"expected #RRGGBB, got {value!r}")
    r, g, b = (int(s[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)
    return h * 360


def random_accent_hex(
    avoid_hue_deg: float | None = None,
    avoid_tolerance: float = 30.0,
) -> str:
    """アイコンの accent 色向けのランダム hex を返す。

    HSV 空間で範囲を絞る: uniform RGB だとグレー / 暗すぎ / 飽和気味の色が
    頻繁に出てアイデンティティ色に使いにくい。S=[0.65, 0.9], V=[0.5, 0.75]
    に収めて「鮮やかだが毒々しくない、明暗どちらの toolbar でも見える」を
    担保する。avoid_hue_deg が指定されていれば、その hue ±tolerance は
    リトライで避ける (= 元のティールと被りにくくする)。
    """
    for _ in range(32):
        h_deg = random.uniform(0, 360)
        if avoid_hue_deg is not None:
            diff = min(abs(h_deg - avoid_hue_deg), 360 - abs(h_deg - avoid_hue_deg))
            if diff < avoid_tolerance:
                continue
        s = random.uniform(0.65, 0.90)
        v = random.uniform(0.50, 0.75)
        r, g, b = colorsys.hsv_to_rgb(h_deg / 360, s, v)
        return "#{:02x}{:02x}{:02x}".format(
            round(r * 255), round(g * 255), round(b * 255)
        )
    # avoid range が広すぎて 32 回外れた場合の fallback: 避ける条件を無視する。
    return random_accent_hex()


def detect_accent_hue_deg(path: Path, sat_min: float) -> float | None:
    """画像中で最も支配的な accent hue を 36 bin ヒストグラムで推定する。

    彩度 sat_min 未満の画素 (白・グレー・黒) は無視し、残った画素を Hue 10°
    刻みで数えて最多 bin の中心値を返す。彩度のある画素が無ければ None。
    これにより「2 回目の recolor は前回塗った色が accent」と自動で切り替わり、
    `--hue-center` を明示しなくても連続実行できる。
    """
    img = Image.open(path).convert("RGBA")
    bins = [0] * 36
    for r, g, b, a in img.get_flattened_data():
        if a == 0:
            continue
        hh, ss, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if ss < sat_min:
            continue
        bins[int(hh * 36) % 36] += 1
    if not any(bins):
        return None
    top = max(range(36), key=lambda i: bins[i])
    return top * 10 + 5


def recolor_in_place(
    path: Path,
    target_hue_deg: float,
    hue_center: float,
    hue_tolerance: float,
    sat_min: float,
) -> int:
    img = Image.open(path).convert("RGBA")
    pixels = img.load()
    assert pixels is not None  # for type checkers
    w, h = img.size
    target_h = target_hue_deg / 360.0
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            h_deg = hh * 360
            # Circular distance on the hue wheel (handles 350° vs 10°).
            diff = min(abs(h_deg - hue_center), 360 - abs(h_deg - hue_center))
            if ss < sat_min or diff > hue_tolerance:
                continue
            nr, ng, nb = colorsys.hsv_to_rgb(target_h, ss, vv)
            pixels[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
            changed += 1
    img.save(path)
    return changed


def main() -> int:
    p = argparse.ArgumentParser(
        description="Recolor accent region of PNG icons in place."
    )
    p.add_argument(
        "--target",
        help="新しい accent color (#RRGGBB)。未指定なら HSV 範囲内で自動生成する。",
    )
    p.add_argument(
        "--hue-center",
        type=float,
        default=None,
        help="元アイコンの accent hue (度)。未指定なら画像から自動検出する。",
    )
    p.add_argument(
        "--hue-tolerance",
        type=float,
        default=30.0,
        help="hue-center から ±何度を差し替え対象にするか (default: 30)",
    )
    p.add_argument(
        "--sat-min",
        type=float,
        default=0.3,
        help="これ未満の彩度は触らない = 白/グレーを温存する (default: 0.3)",
    )
    p.add_argument("paths", nargs="+", type=Path, help="編集対象の PNG (複数可)")
    args = p.parse_args()

    # ランダム生成時に「元 accent と被らない」ようにしたいので、画像から
    # 代表 hue を 1 つ拾う。複数画像の場合は最初の画像を代表として使う
    # (同一 brain の 48/128 は同デザイン前提)。
    avoid_hue_for_random: float | None = args.hue_center
    if args.target is None and avoid_hue_for_random is None:
        for path in args.paths:
            if path.is_file():
                avoid_hue_for_random = detect_accent_hue_deg(path, args.sat_min)
                break

    if args.target:
        target_hex = args.target
    else:
        target_hex = random_accent_hex(
            avoid_hue_deg=avoid_hue_for_random,
            avoid_tolerance=args.hue_tolerance,
        )
        print(f"{_RECOLOR_ICON_TEXT} random target color: {target_hex}")

    try:
        target_hue_deg = hex_to_hue_deg(target_hex)
    except ValueError as e:
        print(f"{_RECOLOR_ICON_TEXT} {e}", file=sys.stderr)
        return 2

    total_changed = 0
    for path in args.paths:
        if not path.is_file():
            print(f"{_RECOLOR_ICON_TEXT} skip (missing): {path}", file=sys.stderr)
            continue
        # 画像ごとに hue_center を決めるので、連続実行しても「前回塗った色」
        # が今回の accent として検出されて正しく差し替わる。
        hue_center = args.hue_center
        if hue_center is None:
            hue_center = detect_accent_hue_deg(path, args.sat_min)
        if hue_center is None:
            print(
                f"{_RECOLOR_ICON_TEXT} {path}: accent hue が検出できませんでした "
                f"(彩度 ≥ {args.sat_min} の画素なし)。skip します。",
                file=sys.stderr,
            )
            continue
        n = recolor_in_place(
            path, target_hue_deg, hue_center, args.hue_tolerance, args.sat_min
        )
        print(
            f"{_RECOLOR_ICON_TEXT} {path}: recolored {n} pixels "
            f"(accent hue: {hue_center:.0f}°)"
        )
        total_changed += n

    if total_changed == 0:
        print(
            f"{_RECOLOR_ICON_TEXT} warning: 対象画素が 0 でした。"
            "--hue-center / --hue-tolerance / --sat-min を見直してください。",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
