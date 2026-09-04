from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets"
OUT_DIR.mkdir(exist_ok=True)


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * max(0, min(1, t)))


def rgba(a: tuple[int, int, int], b: tuple[int, int, int], t: float, alpha: int = 255) -> tuple[int, int, int, int]:
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t), alpha)


def make_gradient_circle(size: int, variant: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size / 2
    r = size / 2
    palettes = [
        ((178, 166, 255), (122, 111, 232)),
        ((204, 193, 255), (137, 124, 236)),
        ((185, 174, 255), (112, 101, 224)),
        ((197, 187, 255), (130, 116, 238)),
    ]
    hi, lo = palettes[variant]
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            d = math.hypot(dx, dy) / r
            if d <= 1:
                light = math.hypot((x - size * 0.72) / size, (y - size * 0.18) / size)
                t = min(1, d * 0.42 + light * 0.72)
                alpha = round(236 - max(0, d - 0.76) * 130)
                px[x, y] = rgba(hi, lo, t, alpha)
    return img


def make_gradient_rect(w: int, h: int, variant: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    palettes = [
        ((118, 110, 232), (66, 56, 174)),
        ((143, 129, 244), (82, 70, 197)),
        ((111, 101, 224), (59, 51, 164)),
        ((130, 119, 240), (74, 62, 188)),
    ]
    hi, lo = palettes[variant]
    for y in range(h):
        for x in range(w):
            t = y / max(1, h - 1) * 0.68 + x / max(1, w - 1) * 0.16
            px[x, y] = rgba(hi, lo, t, 245)
    return img


def rounded_alpha(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def render_mark(variant: int) -> Image.Image:
    # Original 64px symbol proportions read as:
    # bar: x13 y10 w18 h27, circle: x13 y20 diameter36.
    # This keeps that relationship exactly at a larger scale.
    s = 13
    bar_w, bar_h = 18 * s, 27 * s
    circle_d = 36 * s
    bar_x, bar_y = 0, 0
    circle_x, circle_y = 0, 10 * s
    symbol_w, symbol_h = 36 * s, 46 * s
    pad = 115

    mark = Image.new("RGBA", (symbol_w, symbol_h), (0, 0, 0, 0))

    circle = make_gradient_circle(circle_d, variant)
    circle_mask = Image.new("L", (symbol_w, symbol_h), 0)
    cd = ImageDraw.Draw(circle_mask)
    cd.ellipse((circle_x, circle_y, circle_x + circle_d - 1, circle_y + circle_d - 1), fill=255)
    mark.alpha_composite(circle, (circle_x, circle_y))

    rect = make_gradient_rect(bar_w, bar_h, variant)
    # Keep the source logo's crisp rectangular feeling, with only a microscopic
    # optical radius so it does not become a capsule or mascot body.
    rect_mask = rounded_alpha((bar_w, bar_h), 2 * s)
    rect.putalpha(rect_mask.point(lambda p: round(p * 0.96)))
    mark.alpha_composite(rect, (bar_x, bar_y))

    overlap = Image.new("RGBA", (symbol_w, symbol_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlap)
    od.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(29, 37, 111, 198))
    overlap.putalpha(ImageChopsMultiply(circle_mask, overlap.getchannel("A")))
    mark.alpha_composite(overlap)

    # Premium, soft internal highlights. All clipped to the logo silhouette.
    silhouette = Image.new("L", (symbol_w, symbol_h), 0)
    silhouette = ImageChopsLighter(silhouette, circle_mask)
    rd = ImageDraw.Draw(silhouette)
    rd.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=2 * s, fill=255)

    hi = Image.new("RGBA", (symbol_w, symbol_h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hd.arc((circle_x + 18 * s, circle_y + 4 * s, circle_x + 35 * s, circle_y + 31 * s), 285, 45, fill=(255, 255, 255, 76), width=2 * s)
    hd.line((bar_x + 3 * s, bar_y + 2 * s, bar_x + bar_w - 4 * s, bar_y + 2 * s), fill=(255, 255, 255, 46), width=2 * s)
    hi.putalpha(ImageChopsMultiply(silhouette, hi.getchannel("A")))
    mark.alpha_composite(hi)

    eye = Image.new("RGBA", (symbol_w, symbol_h), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eye)
    if variant == 0:
        eyes = [(13.8 * s, 24.2 * s), (18.0 * s, 24.0 * s)]
        for ex, ey in eyes:
            ed.rounded_rectangle((ex - 0.9 * s, ey - 3.2 * s, ex + 0.9 * s, ey + 3.2 * s), radius=0.9 * s, fill=(255, 255, 255, 235))
    elif variant == 1:
        eyes = [(14.0 * s, 24.0 * s), (18.3 * s, 23.8 * s)]
        for ex, ey in eyes:
            ed.ellipse((ex - 1.3 * s, ey - 3.2 * s, ex + 1.3 * s, ey + 3.2 * s), fill=(22, 20, 52, 238))
            ed.ellipse((ex - 0.75 * s, ey - 2.35 * s, ex + 0.25 * s, ey - 1.25 * s), fill=(255, 255, 255, 220))
    elif variant == 2:
        eyes = [(14.5 * s, 24.5 * s), (17.8 * s, 24.4 * s)]
        for ex, ey in eyes:
            ed.rounded_rectangle((ex - 0.65 * s, ey - 2.4 * s, ex + 0.65 * s, ey + 2.4 * s), radius=0.65 * s, fill=(255, 255, 255, 220))
    else:
        eyes = [(14.2 * s, 24.0 * s), (18.2 * s, 24.0 * s)]
        for ex, ey in eyes:
            ed.rounded_rectangle((ex - 1.3 * s, ey - 0.75 * s, ex + 1.3 * s, ey + 0.75 * s), radius=0.75 * s, fill=(255, 255, 255, 226))

    glow = eye.filter(ImageFilter.GaussianBlur(4 * s))
    glow_tint = Image.new("RGBA", (symbol_w, symbol_h), (151, 124, 255, 0))
    glow_tint.putalpha(glow.getchannel("A").point(lambda p: round(p * 0.36)))
    mark.alpha_composite(glow_tint)
    mark.alpha_composite(eye)

    aura = silhouette.filter(ImageFilter.GaussianBlur(9 * s))
    aura_img = Image.new("RGBA", (symbol_w, symbol_h), (126, 102, 255, 0))
    aura_img.putalpha(aura.point(lambda p: round(p * 0.18)))

    out = Image.new("RGBA", (symbol_w + pad * 2, symbol_h + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(aura_img, (pad, pad))
    out.alpha_composite(mark, (pad, pad))
    return out


def ImageChopsMultiply(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.multiply(a, b)


def ImageChopsLighter(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.lighter(a, b)


def main() -> None:
    marks = [render_mark(i) for i in range(4)]
    bg = Image.new("RGBA", (1600, 1600), (250, 248, 255, 255))
    positions = [(220, 180), (900, 180), (220, 880), (900, 880)]

    names = ["slot_pair", "gloss_pair", "tiny_pair", "sleepy_pair"]
    for mark, pos, name in zip(marks, positions, names):
        bg.alpha_composite(mark, pos)
        mark.save(OUT_DIR / f"sixshop-ai-logo-{name}.png")

    bg.save(OUT_DIR / "sixshop-ai-logo-eye-tests.png")
    print(OUT_DIR / "sixshop-ai-logo-eye-tests.png")


if __name__ == "__main__":
    main()
