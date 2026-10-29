#!/usr/bin/env python3
"""
Generates a 1024x1024 modern Sapphire-Obsidian AppIcon.png for GoogleCloudExplorer
using 100% Python 3.10+ standard library (struct + zlib + math).
"""
import math
import struct
import zlib
from pathlib import Path


def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # RGB 8-bit
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


def generate_icon(out_path: Path, size: int = 1024) -> None:
    cx = cy = size / 2.0
    rows: list[bytes] = []

    for y in range(size):
        ny = (y - cy) / (size / 2.0)
        row = bytearray(size * 3)
        idx = 0
        for x in range(size):
            nx = (x - cx) / (size / 2.0)
            dist = math.hypot(nx, ny)

            # Deep obsidian-to-sapphire radial + diagonal mesh background
            diag = (nx + ny) * 0.5
            r = 8.0 + max(0.0, 1.0 - dist * 0.85) * 18.0 + max(0.0, -diag) * 20.0
            g = 15.0 + max(0.0, 1.0 - dist * 0.85) * 44.0 + max(0.0, -diag) * 48.0
            b = 34.0 + max(0.0, 1.0 - dist * 0.80) * 112.0 + max(0.0, -diag) * 85.0

            # Outer orbital SLA ring (radius ~0.64)
            ring1 = abs(dist - 0.64)
            if ring1 < 0.032:
                t = 1.0 - (ring1 / 0.032)
                t = t * t
                # Google Blue -> Emerald -> Amber angular gradient
                angle = (math.atan2(ny, nx) + math.pi) / (2.0 * math.pi)
                if angle < 0.55:
                    cr, cg, cb = 66.0, 133.0, 244.0
                elif angle < 0.82:
                    cr, cg, cb = 52.0, 168.0, 83.0
                else:
                    cr, cg, cb = 251.0, 188.0, 4.0
                r = r * (1.0 - t) + cr * t
                g = g * (1.0 - t) + cg * t
                b = b * (1.0 - t) + cb * t

            # Inner glowing globe sphere (radius 0.44)
            if dist < 0.44:
                sphere_z = math.sqrt(max(0.0, 0.44 * 0.44 - nx * nx - ny * ny)) / 0.44
                # Specular highlight top-left
                spec = max(0.0, (-nx * 0.55 - ny * 0.55 + sphere_z * 0.62)) ** 4
                sr = 18.0 + 48.0 * sphere_z + 150.0 * spec
                sg = 52.0 + 108.0 * sphere_z + 170.0 * spec
                sb = 128.0 + 115.0 * sphere_z + 110.0 * spec

                # Subtle latitude / longitude grid lines on sphere
                lat_band = abs((ny / 0.44) * 3.0 - round((ny / 0.44) * 3.0))
                lon_angle = math.atan2(nx, max(0.08, sphere_z * 0.44))
                lon_band = abs(lon_angle * 2.6 - round(lon_angle * 2.6))
                if lat_band < 0.055 or lon_band < 0.055:
                    sr = min(255.0, sr + 48.0)
                    sg = min(255.0, sg + 72.0)
                    sb = min(255.0, sb + 95.0)

                r, g, b = sr, sg, sb

            # Regional active beacon nodes on globe
            for bx, by, br, bg, bb in (
                (-0.16, -0.10, 52.0, 235.0, 130.0),   # Low CO2 Emerald node
                (0.14, -0.06, 110.0, 180.0, 255.0),   # Sapphire node
                (0.05, 0.16, 255.0, 204.0, 64.0),     # Gold SLA node
            ):
                bdist = math.hypot(nx - bx, ny - by)
                if bdist < 0.055:
                    bt = (1.0 - bdist / 0.055) ** 1.6
                    r = r * (1.0 - bt) + br * bt
                    g = g * (1.0 - bt) + bg * bt
                    b = b * (1.0 - bt) + bb * bt

            row[idx] = max(0, min(255, int(r)))
            row[idx + 1] = max(0, min(255, int(g)))
            row[idx + 2] = max(0, min(255, int(b)))
            idx += 3
        rows.append(bytes(row))

    write_png(out_path, size, size, rows)
    print(f"[AppIcon] Generated {size}x{size} icon -> {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parent.parent
        / "GoogleCloudExplorer"
        / "GoogleCloudExplorer"
        / "Assets.xcassets"
        / "AppIcon.appiconset"
        / "AppIcon.png"
    )
    generate_icon(target, 1024)
