#!/usr/bin/env python3
"""Generate Context macOS app icon assets for AppIcon.appiconset."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
ICONSET = REPO / "DesktopApp" / "DesktopApp" / "Assets.xcassets" / "AppIcon.appiconset"

BG = (15, 17, 21, 255)
ACCENT = (124, 156, 255, 255)
ACCENT_DEEP = (168, 85, 247, 255)
SPARKLE = (243, 244, 246, 255)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _blend(c1: tuple[int, int, int, int], c2: tuple[int, int, int, int], t: float) -> tuple[int, int, int, int]:
    return tuple(_lerp(c1[i], c2[i], t) for i in range(4))  # type: ignore[return-value]


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size * 0.08
    radius = size * 0.22
    draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=radius, fill=BG)

    inner_pad = size * 0.18
    inner_radius = size * 0.16
    for y in range(int(inner_pad), int(size - inner_pad)):
        t = (y - inner_pad) / (size - 2 * inner_pad)
        color = _blend(ACCENT, ACCENT_DEEP, t)
        draw.line([(inner_pad, y), (size - inner_pad, y)], fill=color)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inner_pad, inner_pad, size - inner_pad, size - inner_pad),
        radius=inner_radius,
        fill=255,
    )
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(int(inner_pad), int(size - inner_pad)):
        t = (y - inner_pad) / (size - 2 * inner_pad)
        color = _blend(ACCENT, ACCENT_DEEP, t)
        ImageDraw.Draw(gradient).line([(inner_pad, y), (size - inner_pad, y)], fill=color)
    img = Image.alpha_composite(img, Image.composite(gradient, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    arm = size * 0.17
    thickness = max(2, int(size * 0.055))

    def sparkle_arm(angle_deg: float) -> None:
        import math

        rad = math.radians(angle_deg)
        dx, dy = math.cos(rad), math.sin(rad)
        x1, y1 = cx + dx * arm * 0.15, cy + dy * arm * 0.15
        x2, y2 = cx + dx * arm, cy + dy * arm
        draw.line([(x1, y1), (x2, y2)], fill=SPARKLE, width=thickness)
        dot_r = thickness * 0.9
        draw.ellipse((x2 - dot_r, y2 - dot_r, x2 + dot_r, y2 + dot_r), fill=SPARKLE)

    for angle in (0, 45, 90, 135):
        sparkle_arm(angle)

    core_r = size * 0.07
    draw.ellipse((cx - core_r, cy - core_r, cx + core_r, cy + core_r), fill=SPARKLE)

    return img


def main() -> None:
    ICONSET.mkdir(parents=True, exist_ok=True)
    master = draw_icon(1024)
    master_path = ICONSET / "icon-1024.png"
    master.save(master_path)

    sizes = {
        "icon-16.png": 16,
        "icon-32.png": 32,
        "icon-64.png": 64,
        "icon-128.png": 128,
        "icon-256.png": 256,
        "icon-512.png": 512,
    }
    for name, px in sizes.items():
        draw_icon(px).save(ICONSET / name)

    contents = {
        "images": [
            {"filename": "icon-16.png", "idiom": "mac", "scale": "1x", "size": "16x16"},
            {"filename": "icon-32.png", "idiom": "mac", "scale": "2x", "size": "16x16"},
            {"filename": "icon-32.png", "idiom": "mac", "scale": "1x", "size": "32x32"},
            {"filename": "icon-64.png", "idiom": "mac", "scale": "2x", "size": "32x32"},
            {"filename": "icon-128.png", "idiom": "mac", "scale": "1x", "size": "128x128"},
            {"filename": "icon-256.png", "idiom": "mac", "scale": "2x", "size": "128x128"},
            {"filename": "icon-256.png", "idiom": "mac", "scale": "1x", "size": "256x256"},
            {"filename": "icon-512.png", "idiom": "mac", "scale": "2x", "size": "256x256"},
            {"filename": "icon-512.png", "idiom": "mac", "scale": "1x", "size": "512x512"},
            {"filename": "icon-1024.png", "idiom": "mac", "scale": "2x", "size": "512x512"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    (ICONSET / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote app icons to {ICONSET}")


if __name__ == "__main__":
    main()
