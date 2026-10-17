#!/usr/bin/env python3
"""Fetch the Sentinel logo from GitHub (pinned commit) and generate Android brand resources.

Idempotent: running twice produces byte-identical files.
Needs: numpy, opencv-python-headless, pillow, and either `gh` (authenticated) or --src FILE.

    python3 tools/brand/fetch_brand.py            # download + generate
    python3 tools/brand/fetch_brand.py --src logo.png
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / "brand.json").read_text())
RES = ROOT / "app/src/main/res"
DEBUG_RES = ROOT / "app/src/debug/res"
COMMON_RES = ROOT / "common/src/main/res"

# density -> (adaptive layer px for 108dp, legacy launcher px for 48dp)
DENSITIES = {"mdpi": (108, 48), "hdpi": (162, 72), "xhdpi": (216, 96), "xxhdpi": (324, 144), "xxxhdpi": (432, 192)}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fetch_logo(src):
    cache = HERE / ".cache" / f"logo-{CFG['sha'][:7]}.png"
    if src:
        return Image.open(src).convert("RGBA")
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        data = subprocess.run(
            ["gh", "api", f"repos/{CFG['repo']}/contents/{CFG['path']}?ref={CFG['sha']}",
             "-H", "Accept: application/vnd.github.raw"],
            check=True, capture_output=True).stdout
        cache.write_bytes(data)
    return Image.open(cache).convert("RGBA")


def fit(logo, box_h, canvas, bg=None, mono=False):
    """Paste the cropped shield, box_h tall, centred on a canvas x canvas image."""
    shield = logo.crop(logo.getchannel("A").getbbox())
    if mono:
        a = np.asarray(shield.getchannel("A"), dtype=np.float32)
        lum = np.asarray(shield.convert("L"), dtype=np.float32)
        a = a * np.clip(lum / 190.0, 0.30, 1.0)
        shield = Image.merge("RGBA", [Image.new("L", shield.size, 255)] * 3 + [Image.fromarray(a.astype(np.uint8))])
    w = round(shield.width * box_h / shield.height)
    shield = shield.resize((w, box_h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (canvas, canvas), bg or (0, 0, 0, 0))
    out.alpha_composite(shield, ((canvas - w) // 2, (canvas - box_h) // 2))
    return out


def legacy(logo, px, bg, round_):
    base = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    if round_:
        d.ellipse((0, 0, px - 1, px - 1), fill=bg + (255,))
    else:
        d.rounded_rectangle((0, 0, px - 1, px - 1), radius=round(px * 0.22), fill=bg + (255,))
    base.alpha_composite(fit(logo, round(px * 0.70), px))
    return base


def save(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def vector_silhouette(logo, out):
    """Clean flat vector for status-bar use: shield outline ring + central lens dot.

    A thresholded render of the photorealistic logo is too noisy at 24dp, so the shape is
    derived from the alpha silhouette only (smoothed outer contour, eroded inner contour).
    """
    crop = logo.crop(logo.getchannel("A").getbbox())
    alpha = np.asarray(crop.getchannel("A"))
    mask = cv2.GaussianBlur(((alpha > 128).astype(np.uint8)) * 255, (0, 0), 3)
    mask = (mask > 128).astype(np.uint8) * 255
    h, w = mask.shape
    scale = 20.0 / h  # 24dp viewport, 2dp padding
    ox, oy = (24 - w * scale) / 2, 2.0
    inset = int(round(2.4 / scale))  # ring thickness ~2.4dp
    inner = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * inset + 1, 2 * inset + 1)))

    def path(m, eps):
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cnts, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, eps, True)[:, 0, :]
        return "M" + "L".join(f"{ox + x * scale:.2f},{oy + y * scale:.2f}" for x, y in c) + "Z"

    ys, xs = np.nonzero(inner)
    cx, cy = ox + xs.mean() * scale, oy + ys.mean() * scale
    r = 3.0
    dot = f"M{cx - r:.2f},{cy:.2f}a{r},{r} 0 1,0 {2 * r},0a{r},{r} 0 1,0 {-2 * r},0Z"
    d = " ".join([path(mask, 1.5), path(inner, 1.5), dot])
    xml = ('<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
           '    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">\n'
           '    <path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="' + d + '"/>\n'
           '</vector>\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml)
    return 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    args = ap.parse_args()
    logo = fetch_logo(args.src)
    assert logo.size == (512, 512), logo.size

    bg, dbg = hex_rgb(CFG["launcher_bg"]), hex_rgb(CFG["debug_bg"])
    for dens, (layer, leg) in DENSITIES.items():
        m = f"mipmap-{dens}"
        save(fit(logo, round(layer * 0.58), layer), RES / m / "ic_launcher_foreground.png")
        save(fit(logo, round(layer * 0.58), layer, mono=True), RES / m / "ic_launcher_monochrome.png")
        save(legacy(logo, leg, bg, False), RES / m / "ic_launcher.png")
        save(legacy(logo, leg, bg, True), RES / m / "ic_launcher_round.png")
        if (DEBUG_RES / m / "ic_launcher.png").exists():
            save(legacy(logo, leg, dbg, False), DEBUG_RES / m / "ic_launcher.png")
            save(legacy(logo, leg, dbg, True), DEBUG_RES / m / "ic_launcher_round.png")

    # adaptive icon definitions point at the PNG layers
    for name in ("ic_launcher", "ic_launcher_round"):
        (RES / "mipmap-anydpi-v26" / f"{name}.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/colorLauncherBackground" />\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
            '    <monochrome android:drawable="@mipmap/ic_launcher_monochrome" />\n'
            '</adaptive-icon>\n')
    (DEBUG_RES / "values" / "sentinel_colors.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        f'    <color name="sentinelLauncherBackgroundDebug">{CFG["debug_bg"]}</color>\n</resources>\n')
    for name in ("ic_launcher", "ic_launcher_round"):  # debug variant: same layers, tinted background
        (DEBUG_RES / "mipmap-anydpi-v26" / f"{name}.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/sentinelLauncherBackgroundDebug" />\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
            '    <monochrome android:drawable="@mipmap/ic_launcher_monochrome" />\n'
            '</adaptive-icon>\n')
    for stale in ("ic_launcher_foreground", "ic_launcher_foreground_round",
                  "ic_launcher_monochrome", "ic_launcher_monochrome_round"):
        (RES / "drawable" / f"{stale}.xml").unlink(missing_ok=True)

    # launcher background colour
    colors = COMMON_RES / "values/colors.xml"
    txt = colors.read_text()
    import re
    txt = re.sub(r'(<color name="colorLauncherBackground">)#[0-9A-Fa-f]{6,8}(</color>)', rf"\g<1>{CFG['launcher_bg']}\g<2>", txt)
    colors.write_text(txt)

    # in-app logo (Compose painterResource) + notification silhouettes
    save(logo, RES / "drawable-nodpi" / "ic_sentinel_logo.png")
    save(fit(logo, 288, 576), RES / "drawable-nodpi" / "ic_sentinel_splash.png")  # Android 12 splash: icon inside 2/3 circle
    n = vector_silhouette(logo, COMMON_RES / "drawable" / "ic_stat_ic_notification.xml")
    vector_silhouette(logo, COMMON_RES / "drawable" / "ic_stat_ic_notification_blue.xml")
    print(f"brand assets generated from {CFG['repo']}@{CFG['sha'][:7]} ({n} notification contours)")


if __name__ == "__main__":
    sys.exit(main())
