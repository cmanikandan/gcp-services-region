#!/usr/bin/env python3
"""
Generates all three 1024x1024 24-bit opaque RGB App Store icon variants
(Light/Default, iOS 18+ Dark, and iOS 18+ Tinted monochrome) for GoogleCloudExplorer
using 100% Python 3.10+ standard library (struct + zlib + math).

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


def render_variant(out_path: Path, mode: str, size: int = 1024) -> None:
    cx = cy = size / 2.0
    rows: list[bytes] = []

    for y in range(size):
        ny = (y - cy) / (size / 2.0)
        row = bytearray(size * 3)
        idx = 0
        for x in range(size):
            nx = (x - cx) / (size / 2.0)
            dist = math.hypot(nx, ny)
            diag = (nx + ny) * 0.5

            if mode == "light":
                # Crisp Royal Sapphire-to-Cobalt gradient canvas for Light Home Screens & App Store
                r = 16.0 + max(0.0, 1.0 - dist * 0.85) * 28.0 + max(0.0, -diag) * 34.0
                g = 56.0 + max(0.0, 1.0 - dist * 0.85) * 68.0 + max(0.0, -diag) * 62.0
                b = 148.0 + max(0.0, 1.0 - dist * 0.80) * 90.0 + max(0.0, -diag) * 40.0
            elif mode == "dark":
                # Deep Obsidian-to-Sapphire night canvas for iOS 18+ Dark Mode
                r = 6.0 + max(0.0, 1.0 - dist * 0.85) * 16.0 + max(0.0, -diag) * 18.0
                g = 11.0 + max(0.0, 1.0 - dist * 0.85) * 38.0 + max(0.0, -diag) * 42.0
                b = 24.0 + max(0.0, 1.0 - dist * 0.80) * 98.0 + max(0.0, -diag) * 78.0
            else:
                # Monochrome black-to-charcoal base for iOS 18+ Tinted Home Screen icons
                lum = 12.0 + max(0.0, 1.0 - dist * 0.85) * 26.0
                r = g = b = lum

            # Outer orbital SLA uptime ring (radius ~0.64)
            ring1 = abs(dist - 0.64)
            if ring1 < 0.034:
                t = (1.0 - (ring1 / 0.034)) ** 2
                if mode == "tinted":
                    cr = cg = cb = 235.0
                else:
                    angle = (math.atan2(ny, nx) + math.pi) / (2.0 * math.pi)
                    if angle < 0.55:
                        cr, cg, cb = (130.0, 195.0, 255.0) if mode == "light" else (66.0, 133.0, 244.0)
                    elif angle < 0.82:
                        cr, cg, cb = 64.0, 224.0, 130.0
                    else:
                        cr, cg, cb = 255.0, 206.0, 68.0
                r = r * (1.0 - t) + cr * t
                g = g * (1.0 - t) + cg * t
                b = b * (1.0 - t) + cb * t

            # Inner 3D Cloud Region Globe sphere (radius 0.44)
            if dist < 0.44:
                sphere_z = math.sqrt(max(0.0, 0.44 * 0.44 - nx * nx - ny * ny)) / 0.44
                spec = max(0.0, (-nx * 0.55 - ny * 0.55 + sphere_z * 0.62)) ** 4

                if mode == "tinted":
                    gl = 60.0 + 135.0 * sphere_z + 60.0 * spec
                    sr = sg = sb = gl
                elif mode == "light":
                    sr = 42.0 + 78.0 * sphere_z + 135.0 * spec
                    sg = 108.0 + 112.0 * sphere_z + 125.0 * spec
                    sb = 212.0 + 43.0 * sphere_z + 60.0 * spec
                else:
                    sr = 18.0 + 48.0 * sphere_z + 150.0 * spec
                    sg = 52.0 + 108.0 * sphere_z + 170.0 * spec
                    sb = 128.0 + 115.0 * sphere_z + 110.0 * spec

                lat_band = abs((ny / 0.44) * 3.0 - round((ny / 0.44) * 3.0))
                lon_angle = math.atan2(nx, max(0.08, sphere_z * 0.44))
                lon_band = abs(lon_angle * 2.6 - round(lon_angle * 2.6))
                if lat_band < 0.055 or lon_band < 0.055:
                    boost = 58.0 if mode == "tinted" else 52.0
                    sr = min(255.0, sr + boost)
                    sg = min(255.0, sg + (boost if mode == "tinted" else 74.0))
                    sb = min(255.0, sb + (boost if mode == "tinted" else 95.0))

                r, g, b = sr, sg, sb

            # Active regional beacon nodes on globe
            beacons = (
                ((-0.16, -0.10, 255.0, 255.0, 255.0), (0.14, -0.06, 240.0, 240.0, 240.0), (0.05, 0.16, 245.0, 245.0, 245.0))
                if mode == "tinted"
                else (
                    (-0.16, -0.10, 68.0, 245.0, 142.0),   # Low CO2 Emerald node
                    (0.14, -0.06, 225.0, 245.0, 255.0),   # Primary Multi-Region node
                    (0.05, 0.16, 255.0, 214.0, 74.0),     # 99.999% SLA Gold node
                )
            )
            for bx, by, br, bg, bb in beacons:
                bdist = math.hypot(nx - bx, ny - by)
                if bdist < 0.058:
                    bt = (1.0 - bdist / 0.058) ** 1.5
                    r = r * (1.0 - bt) + br * bt
                    g = g * (1.0 - bt) + bg * bt
                    b = b * (1.0 - bt) + bb * bt

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
