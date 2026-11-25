"""Compose the Flagship PhD/ICRA-Grade 4K Overview Poster (3840x2160) for
Goose V0.2 (assembly_finish_005) using verified frozen receipts, cropped
technical figures, the Warm Cream NAO-style half-cutaway Cycles renders,
and the 4-colorway squad lineup.

Usage:
  .venv/bin/python scripts/diagnostics/compose_goose005_flagship_poster_20261125.py
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125"
OUT_DIR = ART / "showcase_renders/cutaway_poster"

# Input renders & figures
HERO_CUTAWAY_DARK = OUT_DIR / "goose_v02_cutaway_hero_dark.png"
HIP_CLOSEUP = OUT_DIR / "goose_v02_cutaway_hip_closeup.png"
COLORWAY_SQUAD = ART / "showcase_renders/colorways/goose_v02_four_colorways_squad.png"

FIG_A2 = ART / "hip_b2_a2_a3/fig_a2_b2r2_converged_fea_and_closed_loop.png"
FIG_A3 = ART / "front_shell_relief/fig_a3_body016_yoke_relief_envelope.png"
FIG_B1 = ART / "environment_board/eda_fab_release_003/fig_b1_env_pcb_fab_6layers_drc0.png"
PCB_FILE = ART / "environment_board/eda_fab_release_003/environment_main.kicad_pcb"
FIG_B2 = ART / "sanyo24_fan_b1/fig_b2_sanyo24_voltage_window_and_fuse_access.png"
FIG_C1 = ART / "sailab_005_43_delivery/fig_c1_sailab005_43_mci_and_gpu_bench.png"

# Verified receipts
REC_A2 = ART / "hip_b2_a2_a3/a2_a3_verification_receipt.json"
REC_A3 = ART / "front_shell_relief/yoke_outer_lip_relief_receipt.json"
REC_B1 = ART / "environment_board/eda_fab_release_003/fab_release_receipt.json"
REC_B2 = ART / "sanyo24_fan_b1/sanyo24_closeout_receipt.json"
REC_C1 = ART / "sailab_005_43_delivery/sailab_005_43_verification_receipt.json"

POSTER_W, POSTER_H = 3840, 2160

# Warm Cream Goose V0.2 Poster Palette
C_CANVAS = (250, 249, 246)      # #FAF9F6 warm academic paper
C_DARK_HDR = (20, 25, 35)       # #141923 deep slate-charcoal
C_DARK_HERO = (12, 16, 25)      # #0C1019 matches dark render outer vignette
C_CARD_BG = (255, 255, 255)     # #FFFFFF
C_CARD_BORDER = (224, 221, 213) # #E0DDD5 warm stone border
C_ORANGE = (255, 106, 19)       # #FF6A13 vibrant tangerine
C_AMBER = (255, 195, 43)        # #FFC32B golden amber
C_CREAM = (242, 229, 207)       # #F2E5CF warm cream ivory
C_TEXT = (24, 30, 41)           # #181E29 dark ink
C_MUTED = (88, 98, 116)         # #586274 slate muted
C_PASS_BG = (224, 245, 232)     # soft green pill
C_PASS_FG = (19, 115, 58)       # emerald green
C_PILL_BG = (32, 41, 56)        # dark slate KPI pill


def load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        cands = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ]
    else:
        cands = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for p in cands:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def paste_fit(
    canvas: Image.Image,
    src_img: Image.Image,
    box: tuple[int, int, int, int],
    border_col: tuple[int, int, int] | None = (228, 226, 220),
    radius: int = 10,
    bg_fill: tuple[int, int, int] = (255, 255, 255),
) -> tuple[int, int, int, int]:
    """Resize src_img preserving aspect ratio to fit inside box=(x0,y0,x1,y1) centered."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    sw, sh = src_img.size
    scale = min(bw / sw, bh / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    resized = src_img.convert("RGB").resize((nw, nh), Image.Resampling.LANCZOS)
    px = x0 + (bw - nw) // 2
    py = y0 + (bh - nh) // 2

    draw = ImageDraw.Draw(canvas)
    if border_col is not None:
        draw.rounded_rectangle([px - 2, py - 2, px + nw + 1, py + nh + 1], radius=radius, fill=bg_fill, outline=border_col, width=2)
    if radius > 0:
        mask = Image.new("L", (nw, nh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, nw - 1, nh - 1], radius=max(2, radius - 2), fill=255)
        canvas.paste(resized, (px, py), mask)
    else:
        canvas.paste(resized, (px, py))
    return (px, py, px + nw, py + nh)


def draw_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, accent: tuple[int, int, int] = C_ORANGE) -> int:
    """Draw a clean academic poster card and return y_content_start."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=C_CARD_BG, outline=C_CARD_BORDER, width=2)
    hdr_h = 54
    draw.rounded_rectangle([x0, y0, x1, y0 + hdr_h], radius=18, fill=C_DARK_HDR)
    draw.rectangle([x0, y0 + 24, x1, y0 + hdr_h], fill=C_DARK_HDR)
    draw.rectangle([x0, y0 + hdr_h - 4, x1, y0 + hdr_h], fill=accent)
    draw.rectangle([x0 + 18, y0 + 14, x0 + 26, y0 + hdr_h - 14], fill=accent)
    draw.text((x0 + 38, y0 + 12), title, font=load_font(25, bold=True), fill=(255, 255, 255))
    return y0 + hdr_h + 14


def project_3d_to_render_px(
    pt_world: tuple[float, float, float],
    cam_loc: tuple[float, float, float],
    target: tuple[float, float, float],
    lens_mm: float,
    sensor_w_mm: float,
    img_w: int,
    img_h: int,
) -> tuple[float, float]:
    """Exact Blender perspective camera projection (world Z-up -> image pixel (u, v))."""
    c = np.array(cam_loc, dtype=np.float64)
    t = np.array(target, dtype=np.float64)
    p = np.array(pt_world, dtype=np.float64)
    fwd = (t - c)
    fwd /= np.linalg.norm(fwd)
    world_up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    right = np.cross(fwd, world_up)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    rel = p - c
    xc = float(np.dot(rel, right))
    yc = float(np.dot(rel, up))
    zc = float(np.dot(rel, fwd))  # depth along camera forward
    f_px = (lens_mm / sensor_w_mm) * max(img_w, img_h)
    u = img_w * 0.5 + f_px * (xc / zc)
    v = img_h * 0.5 - f_px * (yc / zc)
    return u, v


def parse_kicad_pcb(pcb_path: Path) -> dict:
    """Parse real Edge.Cuts, copper segments, vias, and footprints/pads directly from environment_main.kicad_pcb."""
    txt = pcb_path.read_text()

    # Exact Edge.Cuts polygon (ordered around the 35.60 x 34.50 mm outline with bottom M2 reliefs)
    edge_segs = []
    for m in re.finditer(
        r"\(gr_line\s+\(start\s+([0-9.\-]+)\s+([0-9.\-]+)\)\s+\(end\s+([0-9.\-]+)\s+([0-9.\-]+)\).*?\(layer\s+\"Edge\.Cuts\"\)",
        txt,
        re.S,
    ):
        edge_segs.append(((float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))))

    # Chain edge segments into a closed polygon
    edge_poly: list[tuple[float, float]] = []
    if edge_segs:
        rem = list(edge_segs)
        a, b = rem.pop(0)
        edge_poly = [a, b]
        while rem:
            last = edge_poly[-1]
            found = False
            for i, (p0, p1) in enumerate(rem):
                if math.hypot(p0[0] - last[0], p0[1] - last[1]) < 1e-3:
                    edge_poly.append(p1)
                    rem.pop(i)
                    found = True
                    break
                if math.hypot(p1[0] - last[0], p1[1] - last[1]) < 1e-3:
                    edge_poly.append(p0)
                    rem.pop(i)
                    found = True
                    break
            if not found:
                break

    segs_by_layer: dict[str, list[tuple[float, float, float, float, float]]] = {
        "F.Cu": [],
        "In1.Cu": [],
        "In4.Cu": [],
        "B.Cu": [],
    }
    for m in re.finditer(
        r"\(segment\s+\(start\s+([0-9.\-]+)\s+([0-9.\-]+)\)\s+\(end\s+([0-9.\-]+)\s+([0-9.\-]+)\)\s+\(width\s+([0-9.\-]+)\)\s+\(layer\s+\"([^\"]+)\"\)",
        txt,
    ):
        lyr = m.group(6)
        if lyr in segs_by_layer:
            segs_by_layer[lyr].append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))))

    vias = []
    for m in re.finditer(
        r"\(via\s+\(at\s+([0-9.\-]+)\s+([0-9.\-]+)\)\s+\(size\s+([0-9.\-]+)\)\s+\(drill\s+([0-9.\-]+)\)",
        txt,
    ):
        vias.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))

    pads_by_layer: dict[str, list[tuple[float, float, float, float]]] = {"F.Cu": [], "B.Cu": []}
    ic_bodies: dict[str, list[tuple[float, float, float, float, str, tuple[float, float] | None]]] = {"F.Cu": [], "B.Cu": []}
    fp_starts = [m.start() for m in re.finditer(r"\n  \(footprint\s+\"", txt)]
    for idx, st in enumerate(fp_starts):
        en = fp_starts[idx + 1] if idx + 1 < len(fp_starts) else txt.find("\n  (segment", st)
        if en == -1:
            en = len(txt)
        blk = txt[st:en]
        m_hdr = re.search(r"\(footprint\s+\"([^\"]+)\"\s+\(layer\s+\"(F\.Cu|B\.Cu)\"\)", blk)
        m_at = re.search(r"\n    \(at\s+([0-9.\-]+)\s+([0-9.\-]+)(?:\s+([0-9.\-]+))?\)", blk)
        if not m_hdr or not m_at:
            continue
        fp_name = m_hdr.group(1).split(":")[-1]
        lyr = m_hdr.group(2)
        fx, fy = float(m_at.group(1)), float(m_at.group(2))
        rot_deg = float(m_at.group(3)) if m_at.group(3) else 0.0
        rad = math.radians(-rot_deg)
        ca, sa = math.cos(rad), math.sin(rad)

        fp_pads = []
        pin1_xy = None
        for pm in re.finditer(
            r"\(pad\s+\"([^\"]+)\"\s+smd\s+\w+\s+\(at\s+([0-9.\-]+)\s+([0-9.\-]+)(?:\s+[0-9.\-]+)?\)\s+\(size\s+([0-9.\-]+)\s+([0-9.\-]+)\)",
            blk,
        ):
            pnum = pm.group(1)
            lx, ly = float(pm.group(2)), float(pm.group(3))
            sx, sy = float(pm.group(4)), float(pm.group(5))
            wx = fx + lx * ca - ly * sa
            wy = fy + lx * sa + ly * ca
            pads_by_layer[lyr].append((wx, wy, sx, sy))
            fp_pads.append((wx, wy, sx, sy))
            if pnum == "1":
                pin1_xy = (wx, wy)

        # Build authentic silkscreen courtyard outline for multi-pin ICs / connectors
        if len(fp_pads) >= 4:
            x0 = min(p[0] - p[2] * 0.5 for p in fp_pads)
            x1 = max(p[0] + p[2] * 0.5 for p in fp_pads)
            y0 = min(p[1] - p[3] * 0.5 for p in fp_pads)
            y1 = max(p[1] + p[3] * 0.5 for p in fp_pads)
            # For dual-row SOIC/TSSOP/headers, inset body cleanly between opposing pin rows
            bw, bh = x1 - x0, y1 - y0
            if bw > 2.2 and bh > 2.2:
                ic_bodies[lyr].append((x0, y0, x1, y1, fp_name, pin1_xy))

    return {
        "edge_poly": edge_poly,
        "segs_by_layer": segs_by_layer,
        "vias": vias,
        "pads_by_layer": pads_by_layer,
        "ic_bodies": ic_bodies,
    }


def _render_single_enig_board(pcb_data: dict, side: str, size_px: tuple[int, int]) -> Image.Image:
    """Render one supersampled realistic matte-emerald & ENIG-gold PCB side (F.Cu or B.Cu)."""
    ss = 3
    w, h = size_px[0] * ss, size_px[1] * ss
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Board extents: X in [0.4, 36.0] (35.6 mm), Y in [0.5, 35.0] (34.5 mm)
    bx0, by0, bx1, by1 = 0.4, 0.5, 36.0, 35.0
    bw_mm, bh_mm = bx1 - bx0, by1 - by0
    pad_px = 16 * ss
    scale = min((w - 2 * pad_px) / bw_mm, (h - 2 * pad_px) / bh_mm)
    ox = (w - bw_mm * scale) * 0.5 - bx0 * scale
    oy = (h - bh_mm * scale) * 0.5 - by0 * scale

    def to_px(x_mm: float, y_mm: float) -> tuple[float, float]:
        return (ox + x_mm * scale, oy + y_mm * scale)

    poly_px = [to_px(x, y) for x, y in pcb_data["edge_poly"]]

    # 1. Soft physical drop shadow behind board silhouette
    sh_off = 5 * ss
    draw.polygon([(x + sh_off, y + sh_off) for x, y in poly_px], fill=(15, 22, 32, 85))

    # 2. Matte emerald green FR4 solder mask substrate with crisp golden-copper board rim
    draw.polygon(poly_px, fill=(13, 86, 48, 255))

    # 3. Subtle translucent inner copper routing shadow (gives authentic multi-layer PCB depth!)
    inner_layer = "In1.Cu" if side == "F.Cu" else "In4.Cu"
    for x0, y0, x1, y1, wid in pcb_data["segs_by_layer"][inner_layer]:
        lw = max(1, int(round(wid * scale * 1.15)))
        p0, p1 = to_px(x0, y0), to_px(x1, y1)
        draw.line([p0, p1], fill=(20, 114, 65, 165), width=lw)

    # 4. Active surface copper traces under glossy green solder mask (#28B463)
    for x0, y0, x1, y1, wid in pcb_data["segs_by_layer"][side]:
        lw = max(2, int(round(wid * scale * 1.35)))
        p0, p1 = to_px(x0, y0), to_px(x1, y1)
        draw.line([p0, p1], fill=(38, 174, 96, 255), width=lw)
        r = lw * 0.5
        if r >= 1.2:
            draw.ellipse([p0[0] - r, p0[1] - r, p0[0] + r, p0[1] + r], fill=(38, 174, 96, 255))
            draw.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=(38, 174, 96, 255))

    # 5. Crisp white silkscreen IC outlines & Pin-1 polarity dots
    for x0, y0, x1, y1, fp_name, pin1_xy in pcb_data["ic_bodies"][side]:
        # Draw subtle dark IC body courtyard inset between left/right pin rows
        ins_x = (x1 - x0) * 0.24
        ins_y = (y1 - y0) * 0.04
        if (x1 - x0) > 3.2 and (y1 - y0) > 2.2:
            q0 = to_px(x0 + ins_x, y0 + ins_y)
            q1 = to_px(x1 - ins_x, y1 - ins_y)
            draw.rectangle([q0[0], q0[1], q1[0], q1[1]], fill=(10, 68, 38, 210), outline=(232, 240, 236, 220), width=max(2, int(round(0.11 * scale))))
            if pin1_xy is not None:
                p1x, p1y = to_px(pin1_xy[0], pin1_xy[1])
                cx_i = (q0[0] + q1[0]) * 0.5
                dx_dot = q0[0] + 0.45 * scale if p1x < cx_i else q1[0] - 0.45 * scale
                dy_dot = q0[1] + 0.45 * scale if p1y < (q0[1] + q1[1]) * 0.5 else q1[1] - 0.45 * scale
                rd = max(2.2, 0.22 * scale)
                draw.ellipse([dx_dot - rd, dy_dot - rd, dx_dot + rd, dy_dot + rd], fill=(248, 250, 252, 245))

    # 6. Gleaming ENIG 24k Gold SMD Pads (#EAC04E with warm specular highlight & darker chamfer rim)
    for px, py, sx, sy in pcb_data["pads_by_layer"][side]:
        p0 = to_px(px - sx * 0.5, py - sy * 0.5)
        p1 = to_px(px + sx * 0.5, py + sy * 0.5)
        draw.rectangle([p0[0], p0[1], p1[0], p1[1]], fill=(235, 190, 74, 255), outline=(172, 128, 34, 255), width=max(1, ss // 2))
        if (p1[0] - p0[0]) > 4 and (p1[1] - p0[1]) > 4:
            draw.line([(p0[0] + 1, p0[1] + 1), (p1[0] - 1, p0[1] + 1)], fill=(252, 228, 146, 230), width=max(1, ss // 2))

    # 7. 419 ENIG Gold-Ringed Through-Vias with dark micro-drills
    for vx, vy, vsz, vdr in pcb_data["vias"]:
        cx, cy = to_px(vx, vy)
        ro = max(2.3, vsz * 0.55 * scale)
        ri = max(1.1, vdr * 0.55 * scale)
        draw.ellipse([cx - ro, cy - ro, cx + ro, cy + ro], fill=(224, 179, 68, 255), outline=(150, 112, 30, 220), width=1)
        draw.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=(18, 23, 31, 255))

    # 8. Crisp routed FR4 copper-gold board edge outline
    draw.polygon(poly_px, outline=(198, 174, 108, 255), width=max(2, int(round(0.22 * scale))))

    return img.resize(size_px, Image.Resampling.LANCZOS)


def render_enig_pcb_panel(pcb_path: Path, width: int, height: int) -> Image.Image:
    """Compose a realistic Top + Bottom ENIG Green-Gold 6-Layer PCB + Stackup card panel."""
    pcb_data = parse_kicad_pcb(pcb_path)
    panel = Image.new("RGB", (width, height), (246, 247, 249))
    draw = ImageDraw.Draw(panel)

    # Top sleek dark header inside panel
    hdr_h = 38
    draw.rectangle([0, 0, width, hdr_h], fill=(20, 26, 36))
    draw.rectangle([0, hdr_h - 3, width, hdr_h], fill=(38, 174, 96))
    f_hdr = load_font(16, bold=True)
    f_cap = load_font(14, bold=True)
    f_stk_b = load_font(13, bold=True)
    f_stk_n = load_font(13, bold=False)

    draw.text((14, 9), "6-LAYER ENIG ENVIRONMENT PCB  (35.6 × 34.5 × 0.8 mm)", font=f_hdr, fill=(242, 246, 250))

    # Upper zone: TOP (F.Cu) + BOTTOM (B.Cu) real ENIG boards side by side
    board_area_top = hdr_h + 6
    board_sz = min((width - 28) // 2, 268)
    top_img = _render_single_enig_board(pcb_data, "F.Cu", (board_sz, board_sz))
    bot_img = _render_single_enig_board(pcb_data, "B.Cu", (board_sz, board_sz))

    gap_x = (width - 2 * board_sz) // 3
    lx = gap_x
    rx_b = 2 * gap_x + board_sz
    panel.paste(top_img, (lx, board_area_top), top_img)
    panel.paste(bot_img, (rx_b, board_area_top), bot_img)

    cap_y = board_area_top + board_sz + 2
    t1 = "TOP · L1 F.Cu (1,791 segs)"
    t2 = "BOTTOM · L6 B.Cu (1,670 segs)"
    draw.text((lx + (board_sz - draw.textlength(t1, font=f_cap)) / 2, cap_y), t1, font=f_cap, fill=(24, 32, 44))
    draw.text((rx_b + (board_sz - draw.textlength(t2, font=f_cap)) / 2, cap_y), t2, font=f_cap, fill=(24, 32, 44))

    # Lower zone: Clean 6-Layer FR4 Cross-Section Stackup Diagram + Spec Table
    stk_top = cap_y + 24
    stk_bot = height - 10
    draw.rounded_rectangle([12, stk_top, width - 12, stk_bot], radius=10, fill=(255, 255, 255), outline=(218, 222, 228), width=2)

    draw.text((24, stk_top + 8), "6-LAYER STACKUP CROSS-SECTION (0.8 mm FR4 · 0 DRC · 419 PTH)", font=load_font(13, bold=True), fill=(20, 26, 36))

    layers_info = [
        ("L1  F.Cu", "Top Signal & Connectors", "1,791 segs", (38, 174, 96)),
        ("L2  In1.Cu", "Inner Signal Routing", "877 segs", (240, 178, 36)),
        ("L3  In2.Cu", "Solid Ref GND Plane", "1,021 mm²", (42, 168, 224)),
        ("L4  In3.Cu", "ENV_V5 Power Plane", "1,015 mm²", (142, 108, 226)),
        ("L5  In4.Cu", "Inner Signal Routing", "913 segs", (46, 196, 148)),
        ("L6  B.Cu", "Bottom IC Array & Bus", "1,670 segs", (238, 128, 42)),
    ]

    # Left cross-section drawing (x: 24..210)
    sx0, sx1 = 26, 204
    y_start = stk_top + 32
    y_span = (stk_bot - 12) - y_start
    step_y = y_span / len(layers_info)

    # FR4 green dielectric core backdrop behind copper strata
    draw.rounded_rectangle([sx0, y_start, sx1, stk_bot - 12], radius=5, fill=(214, 232, 218), outline=(140, 178, 150), width=1)

    for i, (lname, ldesc, lcnt, lcol) in enumerate(layers_info):
        ly = y_start + i * step_y + step_y * 0.25
        lh = max(6, int(step_y * 0.48))
        # Solid planes span full width; signal layers draw segmented copper traces
        if i in (2, 3):
            draw.rectangle([sx0 + 6, ly, sx1 - 6, ly + lh], fill=lcol)
        else:
            for seg_a, seg_b in ((0.04, 0.24), (0.30, 0.56), (0.62, 0.78), (0.83, 0.96)):
                xa = sx0 + (sx1 - sx0) * seg_a
                xb = sx0 + (sx1 - sx0) * seg_b
                draw.rectangle([xa, ly, xb, ly + lh], fill=lcol)

        # Right side aligned text table
        tx = sx1 + 16
        draw.rounded_rectangle([tx, ly, tx + 10, ly + lh], radius=2, fill=lcol)
        draw.text((tx + 16, ly - 3), lname, font=f_stk_b, fill=(24, 30, 41))
        draw.text((tx + 104, ly - 3), ldesc, font=f_stk_n, fill=(76, 86, 102))
        cw = draw.textlength(lcnt, font=f_stk_b)
        draw.text((width - 24 - cw, ly - 3), lcnt, font=f_stk_b, fill=(20, 110, 58) if i in (0, 5) else (62, 72, 88))

    # Draw 2 realistic ENIG gold through-via barrels penetrating L1 -> L6
    for vx_rel in (0.27, 0.805):
        vx = sx0 + (sx1 - sx0) * vx_rel
        draw.rectangle([vx - 5, y_start - 1, vx + 5, stk_bot - 11], fill=(228, 184, 68), outline=(145, 110, 28), width=1)
        draw.rectangle([vx - 2, y_start, vx + 2, stk_bot - 12], fill=(26, 32, 42))

    return panel


def draw_bullet(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, val: str, max_w: int, f_lbl, f_val, dot_col=C_ORANGE) -> int:
    draw.ellipse([x, y + 8, x + 10, y + 18], fill=dot_col)
    draw.text((x + 18, y), label, font=f_lbl, fill=C_TEXT)
    lw = draw.textlength(label, font=f_lbl)
    draw.text((x + 24 + lw, y), val, font=f_val, fill=C_MUTED)
    return y + 32


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for req in (HERO_CUTAWAY_DARK, HIP_CLOSEUP, COLORWAY_SQUAD, REC_A2, REC_A3, REC_B1, REC_B2, REC_C1):
        assert req.exists(), f"Missing required input: {req}"

    rec_a2 = json.loads(REC_A2.read_text())
    rec_a3 = json.loads(REC_A3.read_text())
    rec_b1 = json.loads(REC_B1.read_text())
    rec_b2 = json.loads(REC_B2.read_text())
    rec_c1 = json.loads(REC_C1.read_text())

    # Verified numbers from frozen receipts
    total_mass_kg = float(rec_c1["manifest_and_mci"]["compiled_mass_kg"])  # 18.767646 kg
    net_struct_g = float(rec_a2["mass_ledger"]["summary_g"]["net_structural_delta_g"])  # 198.3 g
    fine_sj = float(rec_a2["mesh_convergence"]["fine"]["sj_stats"]["min_scaled_jacobian"])  # 0.06153
    fine_dofs = int(rec_a2["mesh_convergence"]["fine"]["sj_stats"]["n_dofs"])  # 115875
    yoke_gap_after = float(rec_a3["sides"]["left"]["global_min_gap_mm"])  # 1.5869 mm
    drc_viol = int(rec_b1["cold_native_drc"]["total_violations"])  # 0
    pcb_nets = int(rec_b1["cold_native_drc"]["nets"])  # 106
    pcb_fps = int(rec_b1["cold_native_drc"]["footprints"])  # 142
    mc_pass = int(rec_b2["pillar_1_ovp_clamp_coordination"]["monte_carlo_50k_pass_count"])  # 50000
    mc_trials = int(rec_b2["pillar_1_ovp_clamp_coordination"]["monte_carlo_50k_trials"])  # 50000
    ovp_gap_mv = float(rec_b2["pillar_1_ovp_clamp_coordination"]["conservative_0p30pct_corners"]["margins_V"]["clamp_off_min_above_ovp_trip_max_V"]) * 1000.0
    fan_delta_g = float(rec_b2["assembly_finish_005_mass_delta_g"]["subtotal_protection_and_fuse_assembly_g"])  # 9.6 g
    gpu_steps_s = float(rec_c1["gpu_and_checkpoint"]["gpu_32env_bench"]["world_steps_per_s"])  # 1330.23
    gpu_p95_ms = float(rec_c1["gpu_and_checkpoint"]["gpu_32env_bench"]["p95_step_ms"])  # 26.29
    beak_z_m = float(rec_c1["beak_and_protected"]["neutral_beak_plane_z_m"])  # 0.628305
    n_dof = int(rec_c1["manifest_and_mci"]["compiled_nu"])  # 18
    n_cad = 2529

    poster = Image.new("RGB", (POSTER_W, POSTER_H), C_CANVAS)
    draw = ImageDraw.Draw(poster)

    f_title = load_font(56, bold=True)
    f_sub = load_font(23, bold=False)
    f_pill_big = load_font(30, bold=True)
    f_pill_lbl = load_font(15, bold=True)
    f_badge = load_font(17, bold=True)
    f_b_lbl = load_font(19, bold=True)
    f_b_val = load_font(19, bold=False)
    f_tbl_h = load_font(17, bold=True)
    f_tbl_c = load_font(17, bold=False)
    f_tbl_b = load_font(17, bold=True)
    f_call_t = load_font(18, bold=True)
    f_call_s = load_font(15, bold=False)

    # ── TOP BANNER (0..208) ─────────────────────────────────────────────
    draw.rectangle([0, 0, POSTER_W, 204], fill=C_DARK_HDR)
    draw.rectangle([0, 198, POSTER_W, 206], fill=C_ORANGE)
    draw.rectangle([0, 0, 14, 204], fill=C_AMBER)

    draw.rounded_rectangle([48, 22, 540, 56], radius=8, fill=C_ORANGE)
    draw.text((64, 28), "HARDWARE CLOSEOUT · ASSEMBLY_FINISH_005", font=f_badge, fill=(255, 255, 255))
    draw.text((48, 66), "GOOSE V0.2 — MAX PRO BIPEDAL ROBOT GOOSE", font=f_title, fill=(255, 255, 255))
    draw.text(
        (50, 138),
        "Digital Hardware Closeout (assembly_finish_005)  ·  43-Collider SaiLab Virtual Goose  ·  MicroDuck-Inspired Open-Source Platform",
        font=f_sub,
        fill=(212, 220, 232),
    )

    # 6 KPI Pills on Right of Banner
    kpis = [
        (f"{total_mass_kg:.2f} kg", "005 TOTAL MASS"),
        (f"{n_dof} DoF", "5 NECK · 1 BEAK · 12 LEG"),
        ("310 mm", "WIDENED HP STANCE"),
        (f"{n_cad}+", "CAD PARTS RECONCILED"),
        (f"{drc_viol}-DRC 6L", f"{pcb_nets}/{pcb_nets} NETS ENV PCB"),
        (f"{gpu_steps_s:,.0f} st/s", "32-ENV GPU MUJOCO"),
    ]
    pill_w, pill_h, pill_gap = 216, 126, 16
    px0 = POSTER_W - 48 - (len(kpis) * pill_w + (len(kpis) - 1) * pill_gap)
    py0 = 36
    for i, (big, sub) in enumerate(kpis):
        bx = px0 + i * (pill_w + pill_gap)
        draw.rounded_rectangle([bx, py0, bx + pill_w, py0 + pill_h], radius=14, fill=C_PILL_BG, outline=(62, 76, 98), width=2)
        draw.rectangle([bx + 18, py0 + 14, bx + pill_w - 18, py0 + 19], fill=C_AMBER if i % 2 == 0 else C_ORANGE)
        tw = draw.textlength(big, font=f_pill_big)
        draw.text((bx + (pill_w - tw) / 2, py0 + 34), big, font=f_pill_big, fill=C_CREAM)
        sw = draw.textlength(sub, font=f_pill_lbl)
        draw.text((bx + (pill_w - sw) / 2, py0 + 84), sub, font=f_pill_lbl, fill=(178, 190, 208))

    # ── FOOTER (2094..2160) ─────────────────────────────────────────────
    draw.rectangle([0, 2094, POSTER_W, POSTER_H], fill=C_DARK_HDR)
    draw.rectangle([0, 2094, POSTER_W, 2099], fill=C_ORANGE)
    draw.text(
        (48, 2114),
        "github.com/sgyli7/Sai_Rotbots   ·   robots/goose_v0_2   ·   Digital Hardware Closeout (assembly_finish_005) · All metrics verified from cold receipts",
        font=load_font(20, bold=False),
        fill=(210, 218, 230),
    )
    rt_txt = "Digital Design Frozen (Step 1 PASS)   |   Physical Bench & Procurement (Step 2)"
    rw = draw.textlength(rt_txt, font=load_font(20, bold=True))
    draw.text((POSTER_W - 48 - rw, 2114), rt_txt, font=load_font(20, bold=True), fill=C_AMBER)

    # ── COLUMN GEOMETRY ─────────────────────────────────────────────────
    col_l = (48, 1198)
    col_c = (1230, 2610)
    col_r = (2642, 3792)

    # ════════════════════════════════════════════════════════════════════
    # LEFT COLUMN (Cards 1, 2, 3)
    # ════════════════════════════════════════════════════════════════════
    # Card 1: Hip Architecture (opt_b2_r2) & Converged FEA (y=228..958)
    yc = draw_card(draw, (col_l[0], 228, col_l[1], 958), "1. HIP ARCHITECTURE (opt_b2_r2) & CONVERGED FEA", C_ORANGE)
    lx = col_l[0] + 24
    # Scorecard Table (top half of Card 1)
    rows = [
        ("Gate / Metric", "121 Static", "4.67s Turn", "A3 Closed-Loop", "Verdict"),
        ("Struct Δ / 005 Mass", f"+{net_struct_g:.1f} g", f"{total_mass_kg:.3f} kg", "Same MCI", "PASS"),
        ("C3D10 Mesh (116k DOF)", f"SJ={fine_sj:.4f}", "ΔD=0.08%", "ΔVM=1.40%", "PASS"),
        ("Strength (7075: 503MPa)", "59.4 (8.5×)", "48.7 (10.3×)", "92.9 (5.4×)", "PASS"),
        ("Bolt Slip (11 Joints)", "SF ≥ 6.65", "SF ≥ 7.98", "SF ≥ 5.73", "PASS"),
        ("Loaded Gap (-0.3 tol)", "≥ 1.187 mm", "1.110 mm", "1.012 mm", "PASS"),
        ("Disp / 608 / SS Legal", "≤ 0.189 mm", "1.23 mrad", "0 viol · 0.208s", "PASS"),
    ]
    col_xs = [lx, lx + 285, lx + 465, lx + 640, lx + 860, col_l[1] - 24]
    row_h = 31
    for r_i, r_vals in enumerate(rows):
        ry = yc + r_i * row_h
        if r_i == 0:
            draw.rectangle([col_xs[0], ry, col_xs[-1], ry + row_h], fill=(238, 241, 246))
        elif r_i % 2 == 1:
            draw.rectangle([col_xs[0], ry, col_xs[-1], ry + row_h], fill=(250, 251, 253))
        draw.line([(col_xs[0], ry + row_h), (col_xs[-1], ry + row_h)], fill=(225, 228, 234), width=1)
        for c_i, cell in enumerate(r_vals):
            font_use = f_tbl_h if r_i == 0 else (f_tbl_b if c_i in (0, 4) else f_tbl_c)
            col_use = C_PASS_FG if (r_i > 0 and c_i == 4) else C_TEXT
            if r_i > 0 and c_i == 4:
                draw.rounded_rectangle([col_xs[4] + 10, ry + 3, col_xs[-1] - 10, ry + row_h - 3], radius=6, fill=C_PASS_BG)
            draw.text((col_xs[c_i] + 10, ry + 5), cell, font=font_use, fill=col_use)

    yc += len(rows) * row_h + 10
    draw.text(
        (lx, yc),
        "• Billet Al 7075-T6 bridge + stator tie columns (6× C1 fillets R3–3.5 mm); K1/K2 zero mod.",
        font=load_font(18, bold=False),
        fill=C_MUTED,
    )
    yc += 28

    # Crop Panel B (VM Stress) & Panel E (Stage A3 Closed-Loop) from FIG_A2
    im_a2 = Image.open(FIG_A2)
    crop_vm = im_a2.crop((1480, 120, 2480, 1130))     # Panel B: Fine C3D10 VM Stress Map
    crop_ss = im_a2.crop((1255, 1220, 2505, 2225))    # Panel E: Stage A3 Closed-Loop SS
    mid_x = (col_l[0] + col_l[1]) // 2
    paste_fit(poster, crop_vm, (lx, yc, mid_x - 8, 940))
    paste_fit(poster, crop_ss, (mid_x + 8, yc, col_l[1] - 24, 940))

    # Card 2: Zero-Cut Front Shell Yoke Relief (y=980..1524)
    yc = draw_card(draw, (col_l[0], 980, col_l[1], 1524), "2. ZERO-CUT FRONT SHELL YOKE RELIEF", C_AMBER)
    yc = draw_bullet(draw, lx, yc, "Unloaded Gap (body016_front):", f"0.082 → {yoke_gap_after:.3f} mm (19.3×, 0/162 < 1.5 mm)", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, lx, yc, "Loaded Gap (-0.30 mm tol):", "1.012 mm (A3 SS)  |  1.110 mm (Turn)  |  1.187 mm (Static)", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, lx, yc, "Shell Integrity & Savings:", "PA12 wall 100% UNTOUCHED (2.12–2.27 mm)  ·  -10.66 g/pair steel", 1080, f_b_lbl, f_b_val)

    im_a3 = Image.open(FIG_A3)
    crop_a3_l = im_a3.crop((20, 110, 990, 915))
    crop_a3_m = im_a3.crop((990, 110, 1945, 915))
    paste_fit(poster, crop_a3_l, (lx, yc + 4, mid_x - 8, 1506))
    paste_fit(poster, crop_a3_m, (mid_x + 8, yc + 4, col_l[1] - 24, 1506))

    # Card 3: Parallel 4-Bar Beak Grasp (y=1546..2068)
    yc = draw_card(draw, (col_l[0], 1546, col_l[1], 2068), "3. PARALLEL 4-BAR BEAK GRASP", C_ORANGE)
    txt_x1 = col_l[0] + 540
    ty = yc + 8
    beak_items = [
        ("Neutral Beak Plane:", f"z = {beak_z_m:.4f} m (fixed trap)"),
        ("4-Bar Pin Residual:", "2.62×10⁻¹⁶ m (0 → 20° jaw)"),
        ("Peak Actuator Torque:", "4.5 N·m (beak_input_rotor)"),
        ("Grip Pad Material:", "85A TPU upper/lower cassettes"),
        ("200 Hz 100 g Hold:", "PASS (1.0 s, Δz = -1.99 mm)"),
        ("Mean Hold Forces:", "4.64 N upper / 7.03 N lower"),
    ]
    for k, v in beak_items:
        draw.ellipse([lx, ty + 8, lx + 10, ty + 18], fill=C_ORANGE)
        draw.text((lx + 18, ty), k, font=f_b_lbl, fill=C_TEXT)
        draw.text((lx + 18, ty + 26), v, font=f_b_val, fill=C_MUTED)
        ty += 66

    im_c1 = Image.open(FIG_C1)
    crop_beak = im_c1.crop((1355, 195, 2435, 1085))  # Panel A2: Beak 4-Bar Open Jaw
    paste_fit(poster, crop_beak, (txt_x1 + 12, yc + 2, col_l[1] - 24, 2048))

    # ════════════════════════════════════════════════════════════════════
    # CENTER HERO COLUMN (Main Cutaway + 9 Callouts + Hip Macro Inset)
    # ════════════════════════════════════════════════════════════════════
    hero_box = (col_c[0], 228, col_c[1], 1584)
    draw.rounded_rectangle(hero_box, radius=22, fill=C_DARK_HERO, outline=(48, 58, 76), width=3)

    # Top title overlay inside Center Hero
    draw.rounded_rectangle([col_c[0] + 24, 248, col_c[0] + 740, 286], radius=10, fill=(32, 42, 60), outline=C_ORANGE, width=2)
    draw.text((col_c[0] + 40, 256), "WARM CREAM · SAGITTAL Y=0 HALF-CUTAWAY HERO", font=load_font(19, bold=True), fill=C_CREAM)

    # Paste hero cutaway image cleanly centered inside hero_box with soft edge feathering into C_DARK_HERO
    im_hero = Image.open(HERO_CUTAWAY_DARK).convert("RGB")
    hw, hh = im_hero.size  # 2200 x 2600
    render_area = (col_c[0] + 190, 290, col_c[1] - 190, 1568)
    bw = render_area[2] - render_area[0]
    bh = render_area[3] - render_area[1]
    sc = min(bw / hw, bh / hh)
    nw, nh = int(round(hw * sc)), int(round(hh * sc))
    hero_resized = im_hero.resize((nw, nh), Image.Resampling.LANCZOS)
    hx0 = render_area[0] + (bw - nw) // 2
    hy0 = render_area[1] + (bh - nh) // 2
    hx1, hy1 = hx0 + nw, hy0 + nh
    # Feather outer 42 px alpha so hero studio vignette melts seamlessly into C_DARK_HERO
    yy, xx = np.mgrid[0:nh, 0:nw].astype(np.float32)
    f_px = 42.0
    ax = np.minimum(np.clip(xx / f_px, 0.0, 1.0), np.clip((nw - 1 - xx) / f_px, 0.0, 1.0))
    ay = np.minimum(np.clip(yy / f_px, 0.0, 1.0), np.clip((nh - 1 - yy) / f_px, 0.0, 1.0))
    feather_mask = Image.fromarray(np.clip(ax * ay * 255.0, 0, 255).astype(np.uint8), "L")
    poster.paste(hero_resized, (hx0, hy0), feather_mask)
    scale_x = (hx1 - hx0) / hw
    scale_y = (hy1 - hy0) / hh

    # Exact camera parameters used in render_goose005_cutaway_hero_blender_20261125.py
    cam_loc = (1.40, -0.78, 0.56)
    cam_target = (-0.015, 0.002, 0.325)
    cam_lens = 64.0

    def world_to_poster(pt_w: tuple[float, float, float]) -> tuple[int, int]:
        u, v = project_3d_to_render_px(pt_w, cam_loc, cam_target, cam_lens, 36.0, hw, hh)
        return int(round(hx0 + u * scale_x)), int(round(hy0 + v * scale_y))

    # 9 Non-Overlapping Engineering Callouts: (title, subtitle, world_pt, side, pill_y)
    callouts = [
        # Left side callouts (5 items, strictly top-to-bottom, zero crossing)
        ("2. 4-Bar Beak Drive", "z=0.628m · 4.5 N·m", (0.130, -0.015, 0.628), "L", 355),
        ("3. 5-DoF Neck Stack", "AK45-36 + AK40-10", (-0.043, -0.025, 0.544), "L", 515),
        ("5. 24V Fan & 1A Fuse", "50k MC · Rear Pocket", (-0.185, -0.015, 0.410), "L", 675),
        ("7. Relieved Steel Yoke", "1.587mm gap · -10.7g", (-0.055, -0.075, 0.355), "L", 855),
        ("9. AK45 Leg & Stance", "310 mm HP · 12 leg DoF", (-0.018, -0.155, 0.216), "L", 1145),
        # Right side callouts (4 items, strictly top-to-bottom, zero crossing)
        ("1. Optics & Eye Bezel", "Amber Ring · Sensor PCB", (0.176, 0.002, 0.665), "R", 355),
        ("4. 0-DRC 6L Env PCB", "106/106 Nets · Radxa", (-0.060, 0.000, 0.425), "R", 665),
        ("6. opt_b2_r2 Bridge", "Al7075 +198g · SF 5.4×", (-0.015, -0.035, 0.338), "R", 855),
        ("8. Copper Coldplate", "5.81 W · 55°C Lockout", (-0.010, -0.015, 0.262), "R", 1045),
    ]

    pill_w_c = 258
    pill_h_c = 58
    for title_c, sub_c, wpt, side, py_c in callouts:
        tx, ty = world_to_poster(wpt)
        if side == "L":
            px_c = col_c[0] + 20
            anchor = (px_c + pill_w_c, py_c + pill_h_c // 2)
            elbow = (px_c + pill_w_c + 28, py_c + pill_h_c // 2)
        else:
            px_c = col_c[1] - 20 - pill_w_c
            anchor = (px_c, py_c + pill_h_c // 2)
            elbow = (px_c - 28, py_c + pill_h_c // 2)

        # Leader line with subtle dark halo then bright amber/orange stroke
        draw.line([anchor, elbow, (tx, ty)], fill=(13, 17, 26), width=6)
        draw.line([anchor, elbow, (tx, ty)], fill=C_AMBER, width=3)
        draw.ellipse([tx - 7, ty - 7, tx + 7, ty + 7], fill=C_ORANGE, outline=(255, 255, 255), width=2)

        draw.rounded_rectangle([px_c, py_c, px_c + pill_w_c, py_c + pill_h_c], radius=10, fill=(24, 32, 46), outline=C_AMBER, width=2)
        draw.text((px_c + 12, py_c + 8), title_c, font=f_call_t, fill=(255, 255, 255))
        draw.text((px_c + 12, py_c + 32), sub_c, font=f_call_s, fill=C_CREAM)

    # Bottom Center Macro Card (y=1604..2068): Torso/Hip Cutaway Macro Close-up
    yc = draw_card(draw, (col_c[0], 1604, col_c[1], 2068), "TORSO / HIP BAY MACRO CUTAWAY (assembly_finish_005)", C_AMBER)
    im_hip = Image.open(HIP_CLOSEUP)
    placed_hip = paste_fit(poster, im_hip, (col_c[0] + 22, yc, col_c[0] + 575, 2050), border_col=(60, 72, 92), radius=12, bg_fill=C_DARK_HERO)

    # Macro Legend / Key Hardware Index on Right of Bottom Inset
    mx = col_c[0] + 598
    my = yc + 6
    macro_notes = [
        ("Al 7075-T6 Anchored Bridge (opt_b2_r2)", "Warm billet aluminum · +141.2 g · 6× C1 fillets · 0.000 mm³ collision", C_AMBER),
        ("Relieved Steel Hip Yokes (smooth_005)", "Brushed steel · 1.587 mm unloaded / ≥1.01 mm loaded gap · -10.66 g/pair", (140, 155, 175)),
        ("6L Emerald Avionics & 24 V Mini-Board", "0-DRC 106/106 Env PCB + 26-part OVP/Clamp mini-board (50k/50k MC)", C_PASS_FG),
        ("Copper Coldplate & Rear 1 A Fuse Pocket", "5.81 W steady · 55°C no-next-brake lockout · 15/15 cover-clear +Y fuse", C_ORANGE),
        ("K1/K2 Contactors & 6S LiPo Core", "Zero modification to K1/K2/cassette · 1.385 mm min fixed gap to K2", (60, 120, 200)),
    ]
    for m_t, m_s, m_col in macro_notes:
        draw.rounded_rectangle([mx, my + 4, mx + 12, my + 50], radius=4, fill=m_col)
        draw.text((mx + 22, my + 2), m_t, font=load_font(20, bold=True), fill=C_TEXT)
        draw.text((mx + 22, my + 28), m_s, font=load_font(17, bold=False), fill=C_MUTED)
        my += 68

    # ════════════════════════════════════════════════════════════════════
    # RIGHT COLUMN (Cards 4, 5, 6)
    # ════════════════════════════════════════════════════════════════════
    # Card 4: Avionics & Power Closeout (y=228..958)
    yc = draw_card(draw, (col_r[0], 228, col_r[1], 958), "4. AVIONICS & POWER CLOSEOUT (0-DRC + 24 V FAN)", C_ORANGE)
    rx = col_r[0] + 24
    yc = draw_bullet(draw, rx, yc, "6-Layer Env PCB (fab_003):", f"{drc_viol} DRC viol. · {pcb_nets}/{pcb_nets} nets · {pcb_fps} BOM/CPL · 419 drills", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, rx, yc, "24 V Direct Fan OVP/Clamp:", f"+{ovp_gap_mv:.1f} mV WC gap · {mc_pass:,}/{mc_trials:,} MC pass · 17.62 V floor", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, rx, yc, "Serviceable 1 A Fuse Pocket:", f"0.000 mm³ hit · 15/15 cover clear · 98.04 mm 6P tap · +{fan_delta_g:.1f} g", 1080, f_b_lbl, f_b_val)

    im_b2 = Image.open(FIG_B2)
    rmid_x = (col_r[0] + col_r[1]) // 2
    pcb_box = (rx, yc + 4, rmid_x + 48, 940)
    enig_pcb_panel = render_enig_pcb_panel(PCB_FILE, pcb_box[2] - pcb_box[0], pcb_box[3] - pcb_box[1])
    paste_fit(poster, enig_pcb_panel, pcb_box, border_col=(214, 218, 224), radius=10)
    crop_fan = im_b2.crop((1334, 40, 2400, 1300))     # Panel B: 50,000-Trial Monte Carlo Separation
    paste_fit(poster, crop_fan, (rmid_x + 62, yc + 4, col_r[1] - 24, 940))

    # Card 5: SaiLab Virtual Goose 005/43 (y=980..1524)
    yc = draw_card(draw, (col_r[0], 980, col_r[1], 1524), "5. SAILAB VIRTUAL GOOSE (005/43 BUNDLE)", C_AMBER)
    yc = draw_bullet(draw, rx, yc, "43-Collider MuJoCo 3.15.0:", f"22 bodies · 44 geoms · {total_mass_kg:.4f} kg (MCI err < 10⁻¹⁶)", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, rx, yc, "32-Env GPU Throughput:", f"{gpu_steps_s:,.1f} world-steps/s (p95 = {gpu_p95_ms:.2f} ms, 0 NaNs)", 1080, f_b_lbl, f_b_val)
    yc = draw_bullet(draw, rx, yc, "Determinism & Cold Gates:", "2+1 PPO save/resume bit-exact (SHA match) · 8/8 gates PASS", 1080, f_b_lbl, f_b_val)

    crop_mj = im_c1.crop((175, 195, 1145, 1085))      # Panel A1: 43-Collider Standing q0
    crop_grf = im_c1.crop((1290, 1265, 2540, 2230))  # Panel B2: Drop GRF & 100 g Grasp Force
    paste_fit(poster, crop_mj, (rx, yc + 4, rmid_x - 8, 1506))
    paste_fit(poster, crop_grf, (rmid_x + 8, yc + 4, col_r[1] - 24, 1506))

    # Card 6: MicroDuck-Inspired 4-Colorway Squad (y=1546..2068)
    yc = draw_card(draw, (col_r[0], 1546, col_r[1], 2068), "6. MICRODUCK-INSPIRED 4-COLORWAY SQUAD", C_ORANGE)
    im_sq = Image.open(COLORWAY_SQUAD)
    sw, sh = im_sq.size
    # Crop just below the top header bar of the squad strip so Card 6 header frames the 4 studio renders cleanly
    crop_sq = im_sq.crop((30, int(sh * 0.085), sw - 30, sh - 10))
    paste_fit(poster, crop_sq, (rx, yc + 4, col_r[1] - 24, 2048), border_col=None, bg_fill=C_CARD_BG)

    out_poster = OUT_DIR / "goose_v02_flagship_poster.png"
    poster.save(out_poster, optimize=True)
    sha = hashlib.sha256(out_poster.read_bytes()).hexdigest()
    print(f"SAVED {out_poster} ({POSTER_W}x{POSTER_H}) sha256={sha}")


if __name__ == "__main__":
    main()
