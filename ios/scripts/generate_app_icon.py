#!/usr/bin/env python3
"""
Generates all three 1024x1024 24-bit opaque RGB App Store icon variants
(Light/Default, iOS 18+ Dark, and iOS 18+ Tinted monochrome) for GoogleCloudExplorer
using 100% Python 3.10+ standard library (struct + zlib + math).

Features an anti-aliased 4-color Google Cloud ribbon emblem with a Gemini AI
4-point sparkle star on a Neo-Bento glass canvas.
Note: Apple App Store Connect strictly requires 1024x1024 PNGs with NO alpha channel
(color type 2 = 24-bit RGB opaque).
"""
import math
import struct
import zlib
from pathlib import Path


def write_png_rgb(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # Color type 2 = Truecolor RGB (8 bits/channel, strictly no alpha transparency)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + r for r in rows)
    compressed = zlib.compress(raw, level=6)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def sd_capsule(px: float, py: float, ax: float, ay: float, bx: float, by: float, r: float) -> float:
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / (bax * bax + bay * bay)))
    return math.hypot(pax - bax * h, pay - bay * h) - r


def cloud_outer_sdf(nx: float, ny: float) -> float:
    # Exact Euclidean union of horizontal base pill + upper cloud dome
    d_base = sd_capsule(nx, ny, -0.25, 0.13, 0.25, 0.13, 0.225)
    d_dome = math.hypot(nx + 0.03, ny + 0.05) - 0.285
    return min(d_base, d_dome)


def cloud_inner_sdf(nx: float, ny: float) -> float:
    # Exact uniform-thickness (0.145) inner cloud cutout
    d_base = sd_capsule(nx, ny, -0.25, 0.13, 0.25, 0.13, 0.080)
    d_dome = math.hypot(nx + 0.03, ny + 0.05) - 0.140
    return min(d_base, d_dome)


def render_variant(out_path: Path, mode: str, size: int = 1024) -> None:
    cx = cy = size / 2.0
    aa = 2.8 / size
    rows: list[bytes] = []

    for y in range(size):
        ny = (y - cy) / (size / 2.0)
        row = bytearray(size * 3)
        idx = 0
        for x in range(size):
            nx = (x - cx) / (size / 2.0)
            dist = math.hypot(nx, ny)
            diag = (nx + ny) * 0.5

            # 1. Background Canvas
            if mode == "light":
                # Crisp Porcelain-to-Sky-Tint studio canvas for Light mode
                r = 245.0 - dist * 14.0 - max(0.0, diag) * 10.0
                g = 248.0 - dist * 12.0 - max(0.0, diag) * 8.0
                b = 255.0 - dist * 5.0
            elif mode == "dark":
                # Deep Cyber-Obsidian to Midnight Sapphire canvas
                r = 9.0 + max(0.0, 1.0 - dist * 0.9) * 15.0 + max(0.0, -diag) * 14.0
                g = 14.0 + max(0.0, 1.0 - dist * 0.9) * 26.0 + max(0.0, -diag) * 24.0
                b = 28.0 + max(0.0, 1.0 - dist * 0.85) * 58.0 + max(0.0, -diag) * 44.0
            else:
                # Monochrome charcoal base for iOS 18+ Tinted Home Screen icons
                lum = 14.0 + max(0.0, 1.0 - dist * 0.85) * 24.0
                r = g = b = lum

            # Subtle orbital halo ring
            if abs(dist - 0.78) < 0.007:
                ring_alpha = 1.0 - abs(dist - 0.78) / 0.007
                if mode == "light":
                    r = r * (1.0 - ring_alpha * 0.16) + 66.0 * (ring_alpha * 0.16)
                    g = g * (1.0 - ring_alpha * 0.16) + 133.0 * (ring_alpha * 0.16)
                    b = b * (1.0 - ring_alpha * 0.16) + 244.0 * (ring_alpha * 0.16)
                elif mode == "dark":
                    r += 32.0 * ring_alpha
                    g += 62.0 * ring_alpha
                    b += 118.0 * ring_alpha

            # 2. Cloud Ribbon Evaluation
            d_outer = cloud_outer_sdf(nx, ny - 0.02)
            d_inner = cloud_inner_sdf(nx, ny - 0.02)

            # Soft drop shadow under cloud
            d_shadow = cloud_outer_sdf(nx - 0.012, ny - 0.055)
            if d_shadow < 0.085 and d_outer > -0.01:
                sh = (1.0 - max(0.0, d_shadow) / 0.085) ** 2 * (0.18 if mode == "light" else 0.44)
                r *= 1.0 - sh
                g *= 1.0 - sh
                b *= 1.0 - sh

            outer_alpha = 1.0 - smoothstep(-aa, aa, d_outer)
            inner_alpha = 1.0 - smoothstep(-aa, aa, d_inner)
            ribbon_alpha = max(0.0, outer_alpha - inner_alpha)

            # 4-Color Google Cloud Ribbon Coloring
            if ribbon_alpha > 0.0:
                ang = math.degrees(math.atan2(ny - 0.04, nx + 0.02))
                if mode == "tinted":
                    if -155.0 <= ang < -52.0:
                        cr = cg = cb = 215.0
                    elif -52.0 <= ang < 42.0:
                        cr = cg = cb = 250.0
                    elif 42.0 <= ang < 128.0:
                        cr = cg = cb = 192.0
                    else:
                        cr = cg = cb = 232.0
                else:
                    if -155.0 <= ang < -52.0:
                        # Upper-Left Dome: Google Red (#EA4335)
                        cr, cg, cb = 234.0, 67.0, 53.0
                    elif -52.0 <= ang < 42.0:
                        # Top-Right Dome & Right Lobe: Google Blue (#4285F4)
                        cr, cg, cb = 66.0, 133.0, 244.0
                    elif 42.0 <= ang < 128.0:
                        # Bottom Base: Google Green (#34A853)
                        cr, cg, cb = 52.0, 168.0, 83.0
                    else:
                        # Left Lobe: Google Yellow (#FBBC04)
                        cr, cg, cb = 251.0, 188.0, 4.0

                    # Subtle 3D satin highlight along the middle of the ribbon
                    mid_dist = abs(d_outer + 0.0725)
                    bevel = max(0.0, 1.0 - mid_dist / 0.0725) ** 1.5
                    cr = min(255.0, cr + bevel * 16.0)
                    cg = min(255.0, cg + bevel * 16.0)
                    cb = min(255.0, cb + bevel * 16.0)

                r = r * (1.0 - ribbon_alpha) + cr * ribbon_alpha
                g = g * (1.0 - ribbon_alpha) + cg * ribbon_alpha
                b = b * (1.0 - ribbon_alpha) + cb * ribbon_alpha

            # 3. Gemini AI 4-Point Sparkle Star at upper-right crest (0.31, -0.25)
            sx = abs(nx - 0.31)
            sy = abs(ny + 0.25)
            star_d = (sx ** 0.58 + sy ** 0.58) - (0.145 ** 0.58)
            star_alpha = 1.0 - smoothstep(-aa * 1.4, aa * 1.4, star_d)
            if star_alpha > 0.0:
                if mode == "tinted":
                    sr = sg = sb = 255.0
                elif mode == "light":
                    t_star = max(0.0, min(1.0, (nx - 0.20 + (ny + 0.35)) * 3.5))
                    sr = 138.0 * (1.0 - t_star) + 36.0 * t_star
                    sg = 68.0 * (1.0 - t_star) + 161.0 * t_star
                    sb = 248.0 * (1.0 - t_star) + 250.0 * t_star
                else:
                    t_star = max(0.0, min(1.0, (nx - 0.20 + (ny + 0.35)) * 3.5))
                    sr = 181.0 * (1.0 - t_star) + 110.0 * t_star
                    sg = 255.0 * (1.0 - t_star) + 235.0 * t_star
                    sb = 46.0 * (1.0 - t_star) + 255.0 * t_star
                r = r * (1.0 - star_alpha) + sr * star_alpha
                g = g * (1.0 - star_alpha) + sg * star_alpha
                b = b * (1.0 - star_alpha) + sb * star_alpha

            row[idx] = max(0, min(255, int(r)))
            row[idx + 1] = max(0, min(255, int(g)))
            row[idx + 2] = max(0, min(255, int(b)))
            idx += 3
        rows.append(bytes(row))

    write_png_rgb(out_path, size, size, rows)
    print(f"[AppIcon:{mode}] Generated {size}x{size} 24-bit RGB -> {out_path.name} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    iconset_dir = (
        Path(__file__).resolve().parent.parent
        / "GoogleCloudExplorer"
        / "GoogleCloudExplorer"
        / "Assets.xcassets"
        / "AppIcon.appiconset"
    )
    render_variant(iconset_dir / "AppIcon.png", "light", 1024)
    render_variant(iconset_dir / "AppIcon-Dark.png", "dark", 1024)
    render_variant(iconset_dir / "AppIcon-Tinted.png", "tinted", 1024)
