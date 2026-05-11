"""Render Lemon Aid app icon (1024x1024) from SVG spec using Pillow.

Mirrors mobile/assets/app_icon/app_icon.svg shapes since cairo backends
(cairosvg / rlPyCairo) are unavailable on this Windows host.
"""
from PIL import Image, ImageDraw, ImageFilter
import math

W = H = 1024
img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
draw = ImageDraw.Draw(img, "RGBA")

# Shadow ellipse: cx=512 cy=820 rx=280 ry=40, #1A1F2E @ 8%
draw.ellipse((512 - 280, 820 - 40, 512 + 280, 820 + 40),
             fill=(0x1A, 0x1F, 0x2E, int(255 * 0.08)))

# Lemon body: radial gradient circle cx=512 cy=540 r=360
# Gradient: 0% #FFE066, 60% #FFD93D, 100% #E8B800, focal at (0.35, 0.30) of bbox
cx, cy, r = 512, 540, 360
bbox_x0, bbox_y0 = cx - r, cy - r
focal_x = bbox_x0 + 0.35 * (2 * r)
focal_y = bbox_y0 + 0.30 * (2 * r)
max_dist = 0.85 * (2 * r)  # SVG radial r=0.85

def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

stop0 = (0xFF, 0xE0, 0x66)
stop1 = (0xFF, 0xD9, 0x3D)
stop2 = (0xE8, 0xB8, 0x00)

lemon = Image.new("RGBA", (W, H), (0, 0, 0, 0))
lpx = lemon.load()
for y in range(cy - r, cy + r + 1):
    for x in range(cx - r, cx + r + 1):
        dx = x - cx
        dy = y - cy
        if dx * dx + dy * dy <= r * r:
            d = math.hypot(x - focal_x, y - focal_y) / max_dist
            d = min(d, 1.0)
            if d < 0.6:
                t = d / 0.6
                col = lerp(stop0, stop1, t)
            else:
                t = (d - 0.6) / 0.4
                col = lerp(stop1, stop2, t)
            lpx[x, y] = (col[0], col[1], col[2], 255)
img = Image.alpha_composite(img, lemon)
draw = ImageDraw.Draw(img, "RGBA")

# Leaf: rotated -28deg around (660, 250), two ellipses (rx=110/92, ry=60/48)
def draw_rotated_ellipse(canvas, cx, cy, rx, ry, angle_deg, color):
    pad = int(max(rx, ry) * 2.2)
    layer = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    ldraw.ellipse((pad - rx, pad - ry, pad + rx, pad + ry), fill=color)
    layer = layer.rotate(angle_deg, resample=Image.BICUBIC)
    canvas.alpha_composite(layer, (cx - pad, cy - pad))

draw_rotated_ellipse(img, 660, 250, 110, 60, 28, (0xB8, 0xE9, 0x94, 255))
draw_rotated_ellipse(img, 660, 250,  92, 48, 28, (0xA8, 0xD9, 0x84, 255))
draw = ImageDraw.Draw(img, "RGBA")

# Eyes
draw.ellipse((430 - 28, 520 - 28, 430 + 28, 520 + 28), fill=(0x1A, 0x1F, 0x2E, 255))
draw.ellipse((594 - 28, 520 - 28, 594 + 28, 520 + 28), fill=(0x1A, 0x1F, 0x2E, 255))

# Cheeks
draw.ellipse((350 - 50, 600 - 32, 350 + 50, 600 + 32),
             fill=(0xFF, 0xB6, 0xC1, int(255 * 0.6)))
draw.ellipse((674 - 50, 600 - 32, 674 + 50, 600 + 32),
             fill=(0xFF, 0xB6, 0xC1, int(255 * 0.6)))

# Mouth: quadratic Bezier from (460,620) ctl (512,660) end (564,620), stroke 14
def quad_bezier(p0, p1, p2, steps=80):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts

pts = quad_bezier((460, 620), (512, 660), (564, 620))
for i in range(len(pts) - 1):
    draw.line([pts[i], pts[i + 1]],
              fill=(0x1A, 0x1F, 0x2E, 255), width=14)
# Round caps
draw.ellipse((460 - 7, 620 - 7, 460 + 7, 620 + 7), fill=(0x1A, 0x1F, 0x2E, 255))
draw.ellipse((564 - 7, 620 - 7, 564 + 7, 620 + 7), fill=(0x1A, 0x1F, 0x2E, 255))

out_path = "assets/app_icon/app_icon.png"
img.convert("RGB").save(out_path, "PNG", optimize=True)
import os
print("OK", out_path, os.path.getsize(out_path), "bytes", img.size)
