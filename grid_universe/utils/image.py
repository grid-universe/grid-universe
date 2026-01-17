"""Image utilities.

Vectorized helpers for lightweight image post-processing used by the renderer.

The primary goal is fast, deterministic recoloring of small RGBA sprite
images (e.g. 16x16 or 32x32) without introducing heavyweight dependencies
or per-pixel Python loops. Operations are implemented with NumPy and operate
on float32 buffers to balance precision and performance.

Key Functions
-------------
recolor_image_keep_tone:
    Re-hues an image to a target color while preserving original per-pixel
    luminance (value channel) and optionally original saturation. This enables
    palette swapping / team coloring while retaining shading.

draw_direction_triangles_on_image:
    Overlays directional arrow/triangle glyphs onto an image to visualize
    movement intent or facing direction, used for debugging pathfinding or
    animating multi-step movements.

Implementation Notes
--------------------
The HSV <-> RGB conversions are fully vectorized and attempt to minimize
branching; alpha is preserved exactly unless explicitly recolored.
"""

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw

# Type aliases for clarity
FloatArray = npt.NDArray[np.float32 | np.float64]
UInt8Array = npt.NDArray[np.uint8]
BoolArray = npt.NDArray[np.bool_]


def _rgb_to_hsv_np(
    r: FloatArray, g: FloatArray, b: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Vectorized RGB->HSV for arrays in [0,1]. Returns H,S,V in [0,1], dtype float32.
    """
    maxc: FloatArray = np.maximum(np.maximum(r, g), b)
    minc: FloatArray = np.minimum(np.minimum(r, g), b)
    v: FloatArray = maxc
    deltac: FloatArray = maxc - minc

    # Avoid division by zero: where maxc == 0, S = 0
    denom: FloatArray = np.where(maxc == 0.0, np.float32(1.0), maxc).astype(np.float32)
    s: FloatArray = np.where(maxc > 0.0, deltac / denom, np.float32(0.0)).astype(
        np.float32
    )

    # Prepare intermediates, guard divide-by-zero with 1.0
    safe_d: FloatArray = np.where(deltac == 0.0, np.float32(1.0), deltac).astype(
        np.float32
    )
    rc: FloatArray = (maxc - r) / safe_d
    gc: FloatArray = (maxc - g) / safe_d
    bc: FloatArray = (maxc - b) / safe_d

    h: FloatArray = np.zeros_like(maxc, dtype=np.float32)
    mask: BoolArray = deltac != 0.0
    r_is_max: BoolArray = (r == maxc) & mask
    g_is_max: BoolArray = (g == maxc) & mask
    b_is_max: BoolArray = (b == maxc) & mask

    h[r_is_max] = (bc - gc)[r_is_max]
    h[g_is_max] = (2.0 + (rc - bc))[g_is_max]
    h[b_is_max] = (4.0 + (gc - rc))[b_is_max]
    h = ((h / 6.0) % 1.0).astype(np.float32)

    return h, s, v


def _hsv_to_rgb_np(
    h: FloatArray, s: FloatArray, v: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Vectorized HSV->RGB for arrays in [0,1]. Returns float32 arrays in [0,1].
    """
    i: npt.NDArray[np.int32] = np.floor(h * 6.0).astype(np.int32)
    f: FloatArray = (h * 6.0 - i).astype(np.float32)
    p: FloatArray = (v * (1.0 - s)).astype(np.float32)
    q: FloatArray = (v * (1.0 - s * f)).astype(np.float32)
    t: FloatArray = (v * (1.0 - s * (1.0 - f))).astype(np.float32)

    i_mod: npt.NDArray[np.int32] = (i % 6).astype(np.int32)

    # np.choose promotes dtype; cast back to float32
    r: FloatArray = np.choose(i_mod, [v, q, p, p, t, v]).astype(np.float32)
    g: FloatArray = np.choose(i_mod, [t, v, v, q, p, p]).astype(np.float32)
    b: FloatArray = np.choose(i_mod, [p, p, t, v, v, q]).astype(np.float32)
    return r, g, b


def recolor_image_keep_tone(
    base: Image.Image,
    target_rgb: tuple[int, int, int],
    keep_saturation: bool = True,
    saturation_mix: float = 0.0,
    min_saturation: float = 0.0,
) -> Image.Image:
    """
    Recolor non-transparent pixels by replacing Hue with target color's Hue,
    preserving per-pixel Value (brightness/tone). Saturation is preserved by default.
    """
    if base.mode != "RGBA":
        base = base.convert("RGBA")

    arr: UInt8Array = np.array(base, dtype=np.uint8)
    r8: UInt8Array = arr[..., 0]
    g8: UInt8Array = arr[..., 1]
    b8: UInt8Array = arr[..., 2]
    a8: UInt8Array = arr[..., 3]

    # Normalize to [0,1] float32
    r: FloatArray = r8.astype(np.float32) / 255.0
    g: FloatArray = g8.astype(np.float32) / 255.0
    b: FloatArray = b8.astype(np.float32) / 255.0

    visible: BoolArray = a8 > 0

    # Convert image to HSV
    _, s, v = _rgb_to_hsv_np(r, g, b)

    # Target hue/saturation
    tr, tg, tb = (
        np.float32(target_rgb[0] / 255.0),
        np.float32(target_rgb[1] / 255.0),
        np.float32(target_rgb[2] / 255.0),
    )
    # Build constant arrays (same shape) with explicit dtype
    r_const: FloatArray = np.full_like(r, tr, dtype=np.float32)
    g_const: FloatArray = np.full_like(g, tg, dtype=np.float32)
    b_const: FloatArray = np.full_like(b, tb, dtype=np.float32)

    th, ts, _tv_unused = _rgb_to_hsv_np(r_const, g_const, b_const)

    # Replace hue with target hue
    h_new: FloatArray = th

    # Saturation strategy
    if keep_saturation and saturation_mix == 0.0:
        s_new: FloatArray = s
    else:
        mix = np.float32(np.clip(saturation_mix, 0.0, 1.0))
        s_new = ((1.0 - mix) * s + mix * ts).astype(np.float32)

    if min_saturation > 0.0:
        s_new = np.maximum(s_new, np.float32(min_saturation)).astype(np.float32)

    # Value stays the same
    v_new: FloatArray = v

    rr, gg, bb = _hsv_to_rgb_np(h_new, s_new, v_new)

    # Write back only for visible pixels
    out: UInt8Array = arr.copy()
    out_r: UInt8Array = (rr * 255.0).astype(np.uint8)
    out_g: UInt8Array = (gg * 255.0).astype(np.uint8)
    out_b: UInt8Array = (bb * 255.0).astype(np.uint8)

    out[..., 0][visible] = out_r[visible]
    out[..., 1][visible] = out_g[visible]
    out[..., 2][visible] = out_b[visible]
    # alpha unchanged
    return Image.fromarray(out, mode="RGBA")


def draw_direction_triangles_on_image(
    image: Image.Image, size: int, dx: int, dy: int, count: int
) -> Image.Image:
    """
    Draw 'count' filled triangles pointing (dx, dy) on the given RGBA image.
    Triangles are centered: the centroid of each triangle is symmetrically arranged
    around the image center. Spacing is between triangle centroids.
    """
    if count <= 0 or (dx, dy) == (0, 0):
        return image

    draw = ImageDraw.Draw(image)
    cx, cy = size // 2, size // 2

    # Triangle geometry (relative to size)
    tri_height = max(4, int(size * 0.16))
    tri_half_base = max(3, int(size * 0.10))
    spacing = max(2, int(size * 0.12))  # distance between triangle centroids

    # Axis-aligned direction and perpendicular
    ux, uy = dx, dy  # points toward the triangle tip
    px, py = -uy, ux  # perpendicular (for base width)

    # Offsets for centroids: 1 -> [0], 2 -> [-0.5s, +0.5s], 3 -> [-s, 0, +s], ...
    offsets = [(i - (count - 1) / 2.0) * spacing for i in range(count)]

    # For an isosceles triangle, the centroid lies 1/3 of the height from the base toward the tip.
    # If C is the centroid, then:
    #   tip = C + (2/3)*tri_height * u
    #   base_center = C - (1/3)*tri_height * u
    tip_offset = (2.0 / 3.0) * tri_height
    base_offset = (1.0 / 3.0) * tri_height

    for off in offsets:
        # Centroid position
        Cx = cx + int(round(ux * off))
        Cy = cy + int(round(uy * off))

        # Tip and base-center positions
        tip_x = int(round(Cx + ux * tip_offset))
        tip_y = int(round(Cy + uy * tip_offset))
        base_x = int(round(Cx - ux * base_offset))
        base_y = int(round(Cy - uy * base_offset))

        # Base vertices around base center along the perpendicular
        p1 = (tip_x, tip_y)
        p2 = (
            int(round(base_x + px * tri_half_base)),
            int(round(base_y + py * tri_half_base)),
        )
        p3 = (
            int(round(base_x - px * tri_half_base)),
            int(round(base_y - py * tri_half_base)),
        )

        draw.polygon([p1, p2, p3], fill=(255, 255, 255, 220), outline=(0, 0, 0, 220))

    return image
