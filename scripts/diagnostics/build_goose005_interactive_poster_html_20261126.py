"""Build a 100% self-contained, offline-ready single-HTML interactive version of the
Goose V0.2 (assembly_finish_005) Flagship Poster.

Features embedded in ONE standalone HTML file (works via file:// double-click or HTTPS):
  1. Real-time Three.js r170 WebGL PBR 3D viewer with embedded dual-half assembly_finish_005 GLB
     - 360° smooth OrbitControls drag/zoom on non-interactive viewport area
     - Toggleable Y<0 (viewer-left) shell: Half-Cutaway / Semi-Transparent X-Ray (with slider) / Full Exterior
     - Live 4-Colorway switcher (Warm Cream, Sky Blue, Graphite, Lavender) with real-time GLSL
       Rolls-Royce twin torso coachline shader on Sky/Graphite/Lavender
     - 9 interactive 3D-projected hotspots & smooth-transition callouts that appear on hover/click
       and highlight the corresponding 3D subsystem mesh group (HL1..HL9)
     - Curated camera fly-to presets (Hero 3/4, Hip Macro, and per-subsystem close-ups) + 360° auto-spin
  2. Real animated SaiLab 43-collider GIFs embedded directly in:
     - Card 3: Parallel 4-Bar Beak Grasp (200 Hz pickup/lift/place)
     - Card 5: SaiLab Virtual Goose Locomotion (PPO v2 43-collider stepping & yaw turn)
  3. Supersampled authentic ENIG green-gold Top/Bottom 6-Layer PCB + 6-Layer FR4 Stackup in Card 4
  4. Interactive Card 6 4-Colorway Squad (click any colorway to live-switch the 3D Goose)
  5. Full-screen Lightbox viewer for all engineering charts, PCB, macro render, and GIFs.

Usage:
  .venv/bin/python scripts/diagnostics/build_goose005_interactive_poster_html_20261126.py
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125"
INTERACTIVE_DIR = ART / "showcase_renders/interactive"
CUTAWAY_DIR = ART / "showcase_renders/cutaway_poster"
COLORWAY_DIR = ART / "showcase_renders/colorways"
THREE_DIR = Path("/tmp/three_bundle")

GLB_GZ_PATH = INTERACTIVE_DIR / "goose_v02_005_interactive.glb.gz"
GIF_BEAK_PATH = INTERACTIVE_DIR / "goose_v02_beak_grasp_43.gif"
GIF_LOCO_PATH = INTERACTIVE_DIR / "goose_v02_sailab_locomotion_43.gif"
HIP_CLOSEUP = CUTAWAY_DIR / "goose_v02_cutaway_hip_closeup.png"

FIG_A2 = ART / "hip_b2_a2_a3/fig_a2_b2r2_converged_fea_and_closed_loop.png"
FIG_A3 = ART / "front_shell_relief/fig_a3_body016_yoke_relief_envelope.png"
PCB_FILE = ART / "environment_board/eda_fab_release_003/environment_main.kicad_pcb"
FIG_B2 = ART / "sanyo24_fan_b1/fig_b2_sanyo24_voltage_window_and_fuse_access.png"
FIG_C1 = ART / "sailab_005_43_delivery/fig_c1_sailab005_43_mci_and_gpu_bench.png"

REC_A2 = ART / "hip_b2_a2_a3/a2_a3_verification_receipt.json"
REC_A3 = ART / "front_shell_relief/yoke_outer_lip_relief_receipt.json"
REC_B1 = ART / "environment_board/eda_fab_release_003/fab_release_receipt.json"
REC_B2 = ART / "sanyo24_fan_b1/sanyo24_closeout_receipt.json"
REC_C1 = ART / "sailab_005_43_delivery/sailab_005_43_verification_receipt.json"

OUT_HTML = INTERACTIVE_DIR / "goose_v02_interactive_poster.html"
OUT_RECEIPT = INTERACTIVE_DIR / "interactive_poster_receipt.json"


def load_poster_module():
    mod_path = ROOT / "scripts/diagnostics/compose_goose005_flagship_poster_20261125.py"
    spec = importlib.util.spec_from_file_location("poster_mod", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def img_to_data_uri(img: Image.Image, max_w: int = 960, fmt: str = "WEBP", quality: int = 90) -> str:
    rgb = img.convert("RGB")
    if rgb.width > max_w:
        nh = max(1, int(round(rgb.height * (max_w / rgb.width))))
        rgb = rgb.resize((max_w, nh), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if fmt.upper() == "WEBP":
        rgb.save(buf, format="WEBP", quality=quality, method=6)
        mime = "image/webp"
    else:
        rgb.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def file_to_data_uri(path: Path, mime: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def gzip_b64_bytes(raw: bytes) -> str:
    return base64.b64encode(gzip.compress(raw, compresslevel=9)).decode("ascii")


def crop_studio_theme_thumb(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # Trim wide studio margins around the centered 3/4 Goose studio shot
    return im.crop((int(w * 0.16), int(h * 0.04), int(w * 0.84), int(h * 0.94)))


def main():
    t0 = time.monotonic()
    INTERACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    required = [
        GLB_GZ_PATH,
        GIF_BEAK_PATH,
        GIF_LOCO_PATH,
        HIP_CLOSEUP,
        FIG_A2,
        FIG_A3,
        PCB_FILE,
        FIG_B2,
        FIG_C1,
        REC_A2,
        REC_A3,
        REC_B1,
        REC_B2,
        REC_C1,
        THREE_DIR / "three.module.min.js",
        THREE_DIR / "BufferGeometryUtils.js",
        THREE_DIR / "GLTFLoader.js",
        THREE_DIR / "OrbitControls.js",
        THREE_DIR / "RoomEnvironment.js",
    ]
    for p in required:
        assert p.exists(), f"Missing required asset: {p}"

    pm = load_poster_module()
    rec_a2 = json.loads(REC_A2.read_text())
    rec_a3 = json.loads(REC_A3.read_text())
    rec_b1 = json.loads(REC_B1.read_text())
    rec_b2 = json.loads(REC_B2.read_text())
    rec_c1 = json.loads(REC_C1.read_text())

    # Verified frozen receipt metrics
    total_mass_kg = float(rec_c1["manifest_and_mci"]["compiled_mass_kg"])
    net_struct_g = float(rec_a2["mass_ledger"]["summary_g"]["net_structural_delta_g"])
    fine_sj = float(rec_a2["mesh_convergence"]["fine"]["sj_stats"]["min_scaled_jacobian"])
    yoke_gap_after = float(rec_a3["sides"]["left"]["global_min_gap_mm"])
    drc_viol = int(rec_b1["cold_native_drc"]["total_violations"])
    pcb_nets = int(rec_b1["cold_native_drc"]["nets"])
    pcb_fps = int(rec_b1["cold_native_drc"]["footprints"])
    mc_pass = int(rec_b2["pillar_1_ovp_clamp_coordination"]["monte_carlo_50k_pass_count"])
    mc_trials = int(rec_b2["pillar_1_ovp_clamp_coordination"]["monte_carlo_50k_trials"])
    ovp_gap_mv = float(rec_b2["pillar_1_ovp_clamp_coordination"]["conservative_0p30pct_corners"]["margins_V"]["clamp_off_min_above_ovp_trip_max_V"]) * 1000.0
    fan_delta_g = float(rec_b2["assembly_finish_005_mass_delta_g"]["subtotal_protection_and_fuse_assembly_g"])
    gpu_steps_s = float(rec_c1["gpu_and_checkpoint"]["gpu_32env_bench"]["world_steps_per_s"])
    gpu_p95_ms = float(rec_c1["gpu_and_checkpoint"]["gpu_32env_bench"]["p95_step_ms"])
    beak_z_m = float(rec_c1["beak_and_protected"]["neutral_beak_plane_z_m"])
    n_dof = int(rec_c1["manifest_and_mci"]["compiled_nu"])
    n_cad = 2529

    # Prepare embedded visual assets
    im_a2 = Image.open(FIG_A2)
    uri_vm = img_to_data_uri(im_a2.crop((1480, 120, 2480, 1130)), max_w=760, fmt="WEBP", quality=92)
    uri_ss = img_to_data_uri(im_a2.crop((1255, 1220, 2505, 2225)), max_w=760, fmt="WEBP", quality=92)

    im_a3 = Image.open(FIG_A3)
    uri_a3_l = img_to_data_uri(im_a3.crop((20, 110, 990, 915)), max_w=740, fmt="WEBP", quality=92)
    uri_a3_m = img_to_data_uri(im_a3.crop((990, 110, 1945, 915)), max_w=740, fmt="WEBP", quality=92)

    enig_pcb_img = pm.render_enig_pcb_panel(PCB_FILE, 720, 620)
    uri_pcb = img_to_data_uri(enig_pcb_img, max_w=720, fmt="WEBP", quality=94)

    im_b2 = Image.open(FIG_B2)
    uri_fan = img_to_data_uri(im_b2.crop((1334, 40, 2400, 1300)), max_w=760, fmt="WEBP", quality=92)

    im_c1 = Image.open(FIG_C1)
    uri_grf = img_to_data_uri(im_c1.crop((1290, 1265, 2540, 2230)), max_w=760, fmt="WEBP", quality=92)

    uri_hip = img_to_data_uri(Image.open(HIP_CLOSEUP), max_w=920, fmt="WEBP", quality=90)

    uri_gif_beak = file_to_data_uri(GIF_BEAK_PATH, "image/gif")
    uri_gif_loco = file_to_data_uri(GIF_LOCO_PATH, "image/gif")

    theme_thumbs = {}
    for cid in ("sky", "graphite", "cream", "lavender"):
        p = COLORWAY_DIR / f"goose_v02_theme_{cid}.png"
        theme_thumbs[cid] = img_to_data_uri(crop_studio_theme_thumb(p), max_w=420, fmt="WEBP", quality=88)

    # Embedded gzipped Three.js r170 ES modules & dual-half 005 GLB
    b64_three = gzip_b64_bytes((THREE_DIR / "three.module.min.js").read_bytes())
    b64_bgu = gzip_b64_bytes((THREE_DIR / "BufferGeometryUtils.js").read_bytes())
    b64_gltf = gzip_b64_bytes((THREE_DIR / "GLTFLoader.js").read_bytes())
    b64_orbit = gzip_b64_bytes((THREE_DIR / "OrbitControls.js").read_bytes())
    b64_room = gzip_b64_bytes((THREE_DIR / "RoomEnvironment.js").read_bytes())
    b64_glb = base64.b64encode(GLB_GZ_PATH.read_bytes()).decode("ascii")

    # 9 Interactive Subsystem Callouts (Blender world XYZ -> converted to Three.js Y-up: [x, z, -y])
    callouts_data = [
        {
            "id": 1,
            "group": "HL1_OPTICS",
            "short": "Optics & Eye",
            "title": "1. Optics & Eye Bezel",
            "sub": "Amber Ring · Sensor PCB",
            "detail": "Recessed optical sensor array with signature amber eye bezel, flush dark faceplate, and low-glare coated camera lens assembly.",
            "anchor": [0.176, 0.665, -0.002],
            "side": "R",
            "slotPct": 12.0,
            "focusCam": [0.56, 0.72, 0.34],
            "focusTarget": [0.13, 0.65, 0.0],
            "internal": False,
        },
        {
            "id": 2,
            "group": "HL2_BEAK",
            "short": "4-Bar Beak",
            "title": "2. 4-Bar Beak Drive",
            "sub": f"z={beak_z_m:.3f}m · 4.5 N·m",
            "detail": f"Parallel 4-bar linkage (2.62×10⁻¹⁶ m pin residual over 0–20° jaw sweep) with 85A TPU grip cassettes; 100 g 200 Hz hold PASS.",
            "anchor": [0.130, 0.628, 0.015],
            "side": "L",
            "slotPct": 12.0,
            "focusCam": [0.54, 0.65, 0.36],
            "focusTarget": [0.11, 0.62, 0.0],
            "internal": False,
        },
        {
            "id": 3,
            "group": "HL3_NECK",
            "short": "5-DoF Neck",
            "title": "3. 5-DoF Neck Stack",
            "sub": "AK45-36 + AK40-10",
            "detail": "5-DoF articulated goose neck column coupling torso avionics to head yaw/pitch/roll with articulated service covers.",
            "anchor": [-0.043, 0.544, 0.025],
            "side": "L",
            "slotPct": 27.5,
            "focusCam": [0.55, 0.60, 0.45],
            "focusTarget": [-0.02, 0.53, 0.0],
            "internal": True,
        },
        {
            "id": 4,
            "group": "HL4_ENV_PCB",
            "short": "6L Env PCB",
            "title": "4. 0-DRC 6L Env PCB",
            "sub": f"{pcb_nets}/{pcb_nets} Nets · Radxa",
            "detail": f"6-layer 0.8 mm FR4 ENIG environment board ({drc_viol} DRC, {pcb_fps} BOM/CPL, 419 PTH drills) stacked with Radxa Zero 3W & power rails.",
            "anchor": [-0.060, 0.425, 0.000],
            "side": "R",
            "slotPct": 34.0,
            "focusCam": [0.36, 0.52, 0.42],
            "focusTarget": [-0.05, 0.41, 0.01],
            "internal": True,
        },
        {
            "id": 5,
            "group": "HL5_FAN_FUSE",
            "short": "24V Fan/Fuse",
            "title": "5. 24V Fan & 1A Fuse",
            "sub": "50k MC · Rear Pocket",
            "detail": f"24 V direct Sanyo fan OVP/clamp mini-board (+{ovp_gap_mv:.1f} mV WC margin, {mc_pass:,}/{mc_trials:,} MC PASS) + cover-clear rear 1 A fuse (+{fan_delta_g:.1f} g).",
            "anchor": [-0.185, 0.410, 0.015],
            "side": "L",
            "slotPct": 43.0,
            "focusCam": [-0.52, 0.49, 0.46],
            "focusTarget": [-0.15, 0.40, 0.01],
            "internal": True,
        },
        {
            "id": 6,
            "group": "HL6_OPT_B2_R2",
            "short": "opt_b2_r2",
            "title": "6. opt_b2_r2 Bridge",
            "sub": f"Al7075 +{net_struct_g:.0f}g · SF 5.4×",
            "detail": "Billet Al 7075-T6 anchored hip bridge & stator tie columns (6× C1 fillets R3–3.5 mm); 116k-DOF C3D10 FEA PASS with 0.000 mm³ collision.",
            "anchor": [-0.015, 0.338, 0.035],
            "side": "R",
            "slotPct": 53.5,
            "focusCam": [0.40, 0.41, 0.46],
            "focusTarget": [-0.02, 0.34, 0.02],
            "internal": True,
        },
        {
            "id": 7,
            "group": "HL7_YOKES",
            "short": "Steel Yoke",
            "title": "7. Relieved Steel Yoke",
            "sub": f"{yoke_gap_after:.3f}mm gap · -10.7g",
            "detail": "Zero-cut front shell relief on steel hip yokes: 19.3× unloaded clearance increase to body016_front (≥1.012 mm loaded), PA12 shell 100% untouched.",
            "anchor": [-0.055, 0.355, 0.075],
            "side": "L",
            "slotPct": 59.0,
            "focusCam": [0.46, 0.42, 0.44],
            "focusTarget": [-0.04, 0.35, 0.06],
            "internal": True,
        },
        {
            "id": 8,
            "group": "HL8_COLDPLATE",
            "short": "Cu Coldplate",
            "title": "8. Copper Coldplate",
            "sub": "5.81 W · 55°C Lockout",
            "detail": "C110 copper brake resistor thermal sink & precharge rail beneath K1/K2 contactors; 5.81 W steady dissipation with 55°C no-next-brake lockout.",
            "anchor": [-0.010, 0.262, 0.015],
            "side": "R",
            "slotPct": 72.0,
            "focusCam": [0.44, 0.30, 0.48],
            "focusTarget": [-0.01, 0.27, 0.01],
            "internal": True,
        },
        {
            "id": 9,
            "group": "HL9_LEGS",
            "short": "AK45 Legs",
            "title": "9. AK45 Leg & Stance",
            "sub": "310 mm HP · 12 leg DoF",
            "detail": "12-DoF bilateral AK45 leg drivetrain with widened 310 mm hip-pitch stance, dual-durometer sole trim + dark rubber tread, validated in 43-collider MuJoCo.",
            "anchor": [-0.018, 0.216, 0.155],
            "side": "L",
            "slotPct": 76.0,
            "focusCam": [0.76, 0.26, 0.72],
            "focusTarget": [-0.01, 0.19, 0.04],
            "internal": False,
        },
    ]

    colorways_js = {
        "cream": {
            "id": "cream",
            "name": "Warm Cream",
            "zh": "奶油白",
            "badge": "WARM CREAM · FLAGSHIP IVORY",
            "shell": "#F2E5CF",
            "accent": "#FF6A13",
            "eyeRing": "#FFC32B",
            "soleAccent": "#FFC32B",
            "dark": "#1B1F24",
            "coachline": None,
            "uiAccent": "#FF6A13",
            "uiAmber": "#FFC32B",
            "shellRough": 0.40,
        },
        "sky": {
            "id": "sky",
            "name": "Sky Blue",
            "zh": "天空蓝",
            "badge": "SKY BLUE · MICRODUCK + RR COACHLINE",
            "shell": "#6BC4E8",
            "accent": "#FF6A13",
            "eyeRing": "#FFB81C",
            "soleAccent": "#FFB81C",
            "dark": "#1A1E24",
            "coachline": "#FFB81C",
            "uiAccent": "#38BDF8",
            "uiAmber": "#FFB81C",
            "shellRough": 0.38,
        },
        "graphite": {
            "id": "graphite",
            "name": "Graphite",
            "zh": "石墨灰",
            "badge": "GRAPHITE · VIOLET RR COACHLINE",
            "shell": "#454952",
            "accent": "#F5C724",
            "eyeRing": "#845EC2",
            "soleAccent": "#845EC2",
            "dark": "#16191E",
            "coachline": "#845EC2",
            "uiAccent": "#9D7CE8",
            "uiAmber": "#F5C724",
            "shellRough": 0.42,
        },
        "lavender": {
            "id": "lavender",
            "name": "Lavender",
            "zh": "薰衣草紫",
            "badge": "LAVENDER · CYAN RR COACHLINE",
            "shell": "#B69CE2",
            "accent": "#F5C724",
            "eyeRing": "#55C4E8",
            "soleAccent": "#8B6BC7",
            "dark": "#1A1E24",
            "coachline": "#55C4E8",
            "uiAccent": "#B69CE2",
            "uiAmber": "#55C4E8",
            "shellRough": 0.40,
        },
    }

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Goose V0.2 — Interactive Flagship Hardware Poster (assembly_finish_005)</title>
<style>
  :root {{
    --canvas: #FAF9F6;
    --hdr: #141923;
    --hero-bg: #0C1019;
    --card-bg: #FFFFFF;
    --card-border: #E0DDD5;
    --orange: #FF6A13;
    --amber: #FFC32B;
    --cream: #F2E5CF;
    --ink: #181E29;
    --muted: #586274;
    --pass-bg: #E0F5E8;
    --pass-fg: #13733A;
    --pill-bg: #202938;
    --active-accent: #FF6A13;
    --active-glow: #FFC32B;
    --ease-out-expo: cubic-bezier(0.22, 1, 0.36, 1);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    background: var(--canvas);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "PingFang SC", "Noto Sans SC", "DejaVu Sans", sans-serif;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* ── TOP BANNER ─────────────────────────────────────────────── */
  .poster-header {{
    background: var(--hdr);
    border-bottom: 4px solid var(--active-accent);
    border-left: 8px solid var(--active-glow);
    padding: 14px 26px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    flex-wrap: wrap;
    transition: border-color 0.4s ease;
  }}
  .hdr-left {{ min-width: 320px; flex: 1 1 540px; }}
  .hdr-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--active-accent);
    color: #fff;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    padding: 4px 11px;
    border-radius: 6px;
    margin-bottom: 6px;
    transition: background 0.4s ease;
  }}
  .hdr-badge .dot {{
    width: 7px; height: 7px; border-radius: 50%; background: #fff;
    box-shadow: 0 0 8px #fff;
    animation: pulse-dot 2s infinite;
  }}
  .hdr-title {{
    color: #fff;
    font-size: clamp(20px, 2.05vw, 32px);
    font-weight: 850;
    letter-spacing: -0.015em;
    line-height: 1.12;
  }}
  .hdr-sub {{
    color: #CFD8E6;
    font-size: clamp(11.5px, 0.88vw, 14px);
    margin-top: 5px;
  }}
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(6, minmax(96px, 1fr));
    gap: 8px;
    flex: 0 1 auto;
  }}
  .kpi-pill {{
    background: var(--pill-bg);
    border: 1px solid #3E4C62;
    border-radius: 10px;
    padding: 8px 10px 9px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.22s var(--ease-out-expo), border-color 0.25s ease;
  }}
  .kpi-pill:hover {{ transform: translateY(-2px); border-color: var(--active-glow); }}
  .kpi-pill::before {{
    content: "";
    position: absolute;
    top: 6px; left: 12px; right: 12px; height: 3px;
    border-radius: 2px;
    background: var(--amber);
  }}
  .kpi-pill:nth-child(even)::before {{ background: var(--orange); }}
  .kpi-val {{
    color: var(--cream);
    font-size: clamp(14px, 1.15vw, 19px);
    font-weight: 800;
    margin-top: 6px;
    line-height: 1.15;
    white-space: nowrap;
  }}
  .kpi-lbl {{
    color: #B2BED0;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-top: 3px;
    white-space: nowrap;
  }}

  /* ── MAIN 3-COLUMN POSTER GRID ──────────────────────────────── */
  .poster-grid {{
    display: grid;
    grid-template-columns: minmax(335px, 1.02fr) minmax(540px, 1.48fr) minmax(335px, 1.02fr);
    gap: 14px;
    padding: 14px 20px 16px;
    max-width: 2400px;
    margin: 0 auto;
    align-items: stretch;
  }}
  .col {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
  }}

  /* ── CARD SHELL ─────────────────────────────────────────────── */
  .card {{
    background: var(--card-bg);
    border: 1.5px solid var(--card-border);
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 2px 10px rgba(20, 25, 35, 0.04);
  }}
  .card-hdr {{
    background: var(--hdr);
    color: #fff;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.03em;
    display: flex;
    align-items: center;
    gap: 9px;
    border-bottom: 3px solid var(--orange);
  }}
  .card-hdr.amber {{ border-bottom-color: var(--amber); }}
  .card-hdr::before {{
    content: "";
    width: 4px; height: 15px; border-radius: 2px;
    background: var(--orange);
    flex-shrink: 0;
  }}
  .card-hdr.amber::before {{ background: var(--amber); }}
  .card-body {{
    padding: 10px 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
  }}

  /* ── SCORECARD TABLE ────────────────────────────────────────── */
  table.scorecard {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10px;
    table-layout: auto;
  }}
  table.scorecard th {{
    background: #EEF1F6;
    color: var(--ink);
    font-weight: 800;
    text-align: left;
    padding: 4px 4px;
    border-bottom: 1px solid #D8DCE4;
    white-space: nowrap;
  }}
  table.scorecard td {{
    padding: 3.5px 4px;
    border-bottom: 1px solid #ECEEF3;
    color: var(--ink);
    white-space: nowrap;
  }}
  table.scorecard tr:nth-child(odd) td {{ background: #FAFBFD; }}
  table.scorecard td:first-child {{ font-weight: 700; white-space: normal; line-height: 1.2; }}
  table.scorecard td:last-child, table.scorecard th:last-child {{ text-align: right; }}
  .pass-pill {{
    display: inline-block;
    background: var(--pass-bg);
    color: var(--pass-fg);
    font-weight: 800;
    font-size: 9.5px;
    padding: 1.5px 5.5px;
    border-radius: 5px;
    letter-spacing: 0.03em;
  }}
  .note-line {{
    font-size: 10.8px;
    color: var(--muted);
    line-height: 1.35;
  }}

  /* ── BULLETS & FIGURE GRIDS ─────────────────────────────────── */
  .bullets {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 4.5px;
    font-size: 11px;
    line-height: 1.38;
  }}
  .bullets li {{
    display: block;
    position: relative;
    padding-left: 12px;
    word-break: break-word;
  }}
  .bullets li::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 5.5px;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--orange);
  }}
  .bullets strong {{ color: var(--ink); margin-right: 4px; }}
  .bullets span {{ color: var(--muted); }}

  .fig-pair {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    flex: 1;
    align-items: stretch;
  }}
  .fig-pair.pcb-split {{ grid-template-columns: 1.15fr 0.85fr; }}
  .fig-box {{
    position: relative;
    background: #F6F7FA;
    border: 1px solid #E2E0D8;
    border-radius: 9px;
    overflow: hidden;
    cursor: zoom-in;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 132px;
    transition: transform 0.25s var(--ease-out-expo), border-color 0.25s ease, box-shadow 0.25s ease;
  }}
  .fig-box:hover {{
    transform: translateY(-1.5px);
    border-color: var(--active-accent);
    box-shadow: 0 6px 18px rgba(20, 25, 35, 0.11);
  }}
  .fig-box img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    background: #fff;
  }}
  .fig-box.dark-bg {{ background: #0D111A; border-color: #2B364A; }}
  .fig-box.dark-bg img {{ background: #0D111A; object-fit: contain; }}
  .live-badge {{
    position: absolute;
    top: 7px; left: 7px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(12, 16, 25, 0.84);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(56, 217, 138, 0.55);
    color: #E7FFF1;
    font-size: 9.5px;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 3px 8px;
    border-radius: 999px;
    pointer-events: none;
    z-index: 2;
  }}
  .live-badge .live-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: #22C55E;
    box-shadow: 0 0 7px #22C55E;
    animation: pulse-dot 1.4s infinite;
  }}
  .fig-cap {{
    position: absolute;
    bottom: 6px; left: 7px; right: 7px;
    background: rgba(14, 19, 29, 0.78);
    backdrop-filter: blur(6px);
    color: #EEF2F8;
    font-size: 9.5px;
    font-weight: 600;
    padding: 3px 7px;
    border-radius: 5px;
    pointer-events: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  /* Card 3 Beak Grasp 2-column split */
  .beak-split {{
    display: grid;
    grid-template-columns: 0.92fr 1.08fr;
    gap: 10px;
    align-items: stretch;
    flex: 1;
  }}
  .beak-specs {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 5px;
  }}
  .beak-item {{
    padding-left: 10px;
    border-left: 2.5px solid var(--orange);
  }}
  .beak-item .bk-k {{ font-size: 11px; font-weight: 800; color: var(--ink); line-height: 1.25; }}
  .beak-item .bk-v {{ font-size: 10.5px; color: var(--muted); line-height: 1.25; }}

  /* ═══════════════════════════════════════════════════════════════
     CENTER HERO 3D STAGE
     ═══════════════════════════════════════════════════════════════ */
  .hero-stage {{
    position: relative;
    background: radial-gradient(ellipse 68% 60% at 50% 45%, #202C42 0%, #111827 48%, #0B0F18 100%);
    border: 2px solid #2C374C;
    border-radius: 18px;
    overflow: hidden;
    min-height: 760px;
    flex: 1 1 760px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 14px 36px rgba(10, 14, 24, 0.28);
    user-select: none;
  }}
  #webgl-canvas {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
    cursor: grab;
    touch-action: none;
  }}
  #webgl-canvas:active {{ cursor: grabbing; }}

  /* Subtle top HUD bar inside 3D Hero */
  .hero-hud-top {{
    position: absolute;
    top: 12px; left: 14px; right: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    pointer-events: none;
    z-index: 12;
  }}
  .hero-mode-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(20, 27, 40, 0.84);
    backdrop-filter: blur(12px);
    border: 1.5px solid var(--active-accent);
    border-radius: 9px;
    padding: 6px 12px;
    color: var(--cream);
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 0.05em;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    transition: border-color 0.35s ease;
  }}
  .hero-mode-pill .mode-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--active-accent);
    box-shadow: 0 0 10px var(--active-accent);
  }}
  .hero-hint {{
    background: rgba(15, 21, 33, 0.72);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 999px;
    padding: 5px 12px;
    color: #CBD5E1;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.01em;
    transition: opacity 0.6s ease;
  }}
  .hero-hint.dimmed {{ opacity: 0.55; }}

  /* Loading overlay while decompressing gzipped 3D GLB */
  .loader-overlay {{
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% 48%, #1C263B 0%, #0C1019 72%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    z-index: 30;
    color: #E2E8F0;
    transition: opacity 0.55s var(--ease-out-expo), visibility 0.55s;
  }}
  .loader-overlay.done {{ opacity: 0; visibility: hidden; pointer-events: none; }}
  .spinner {{
    width: 42px; height: 42px;
    border-radius: 50%;
    border: 3px solid rgba(255, 195, 43, 0.18);
    border-top-color: var(--amber);
    animation: spin 0.85s linear infinite;
  }}
  .loader-txt {{ font-size: 12.5px; font-weight: 700; letter-spacing: 0.04em; color: var(--cream); }}
  .loader-sub {{ font-size: 11px; color: #94A3B8; }}

  /* SVG Animated Leader Lines */
  #leader-svg {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 10;
  }}
  .leader-path-halo {{
    fill: none;
    stroke: rgba(11, 15, 24, 0.82);
    stroke-width: 5.5;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0;
    transition: opacity 0.28s var(--ease-out-expo);
  }}
  .leader-path {{
    fill: none;
    stroke: var(--active-glow);
    stroke-width: 2.3;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 600;
    stroke-dashoffset: 600;
    opacity: 0;
    transition: stroke-dashoffset 0.42s var(--ease-out-expo), opacity 0.25s ease, stroke 0.35s ease;
    filter: drop-shadow(0 0 5px rgba(255, 195, 43, 0.55));
  }}
  .leader-group.visible .leader-path-halo {{ opacity: 1; }}
  .leader-group.visible .leader-path {{ opacity: 1; stroke-dashoffset: 0; }}
  .leader-group.active .leader-path {{ stroke: var(--active-accent); stroke-width: 2.8; }}

  /* 3D Projected Hotspot Pins — HIDDEN by default so Goose silhouette stays 100% unobstructed; fade in on hover/select */
  #pin-layer {{
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 11;
  }}
  .hotspot-pin {{
    position: absolute;
    width: 24px; height: 24px;
    margin-left: -12px; margin-top: -12px;
    border-radius: 50%;
    background: rgba(20, 27, 40, 0.90);
    border: 2px solid var(--active-glow);
    color: #fff;
    font-size: 10.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    pointer-events: none;
    opacity: 0;
    transform: scale(0.5);
    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.5);
    transition: transform 0.28s var(--ease-out-expo), opacity 0.24s ease, background 0.22s ease, border-color 0.22s ease;
  }}
  .hotspot-pin.visible {{
    opacity: 0.94;
    pointer-events: auto;
    transform: scale(1.0);
  }}
  .hotspot-pin::after {{
    content: "";
    position: absolute;
    inset: -5px;
    border-radius: 50%;
    border: 1.5px solid var(--active-glow);
    opacity: 0;
    pointer-events: none;
  }}
  .hotspot-pin.visible::after {{
    opacity: 0.55;
    animation: pin-ripple 2.1s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
  }}
  .hotspot-pin.visible.occluded {{ opacity: 0.45; transform: scale(0.86); }}
  .hotspot-pin.active {{
    background: var(--active-accent);
    border-color: #fff;
    transform: scale(1.22);
    opacity: 1 !important;
    pointer-events: auto;
    z-index: 25;
    box-shadow: 0 0 18px var(--active-accent), 0 0 0 4px rgba(255, 255, 255, 0.18);
  }}
  .hotspot-pin.active::after {{
    border-color: var(--active-accent);
    opacity: 0.92;
  }}

  /* Floating Zoom Rail (+ / 1.0x / -) anchored cleanly above bottom dock with zero overlap */
  .zoom-rail {{
    position: absolute;
    right: 14px;
    bottom: 112px;
    z-index: 21;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: rgba(15, 21, 34, 0.82);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 10px;
    padding: 3px;
    gap: 2px;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.42);
  }}
  .zoom-btn {{
    width: 28px; height: 26px;
    border: none;
    border-radius: 7px;
    background: transparent;
    color: #E2E8F0;
    font-size: 16px;
    font-weight: 700;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.18s ease, color 0.18s ease;
  }}
  .zoom-btn:hover {{ background: rgba(255, 255, 255, 0.14); color: #fff; }}
  .zoom-readout {{
    font-size: 9.5px;
    font-weight: 800;
    color: var(--cream);
    padding: 2px 3px;
    letter-spacing: 0.02em;
    min-width: 28px;
    text-align: center;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  }}

  /* 9 Smooth-Transition Side Callout Cards (Compact Pill -> Smooth Animated Reveal) */
  #callout-layer {{
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 14;
  }}
  .callout-card {{
    position: absolute;
    pointer-events: auto;
    cursor: pointer;
    width: 136px;
    border-radius: 9px;
    background: rgba(16, 22, 34, 0.48);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 195, 43, 0.24);
    padding: 5px 8px;
    color: #fff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.24);
    transform-origin: left center;
    transform: translateY(-50%) scale(0.95);
    opacity: 0.56;
    transition:
      opacity 0.32s var(--ease-out-expo),
      transform 0.34s var(--ease-out-expo),
      width 0.34s var(--ease-out-expo),
      background 0.28s ease,
      border-color 0.28s ease,
      box-shadow 0.32s ease;
  }}
  .callout-card.side-L {{ left: 12px; transform-origin: left center; }}
  .callout-card.side-R {{ right: 12px; transform-origin: right center; }}

  .callout-card .cc-head {{
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  .callout-card .cc-num {{
    width: 18px; height: 18px;
    border-radius: 5px;
    background: rgba(255, 195, 43, 0.18);
    border: 1px solid rgba(255, 195, 43, 0.6);
    color: var(--amber);
    font-size: 10px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: background 0.25s ease, color 0.25s ease;
  }}
  .callout-card .cc-title {{
    font-size: 11px;
    font-weight: 800;
    color: #F1F5F9;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .callout-card .cc-t-full {{ display: none; }}
  .callout-card.show-sub .cc-t-short,
  .callout-card:hover .cc-t-short,
  .callout-card.active .cc-t-short {{ display: none; }}
  .callout-card.show-sub .cc-t-full,
  .callout-card:hover .cc-t-full,
  .callout-card.active .cc-t-full {{ display: inline; }}
  .callout-card .cc-body {{
    max-height: 0;
    opacity: 0;
    overflow: hidden;
    transform: translateY(-4px);
    transition: max-height 0.36s var(--ease-out-expo), opacity 0.28s ease, transform 0.32s var(--ease-out-expo), margin-top 0.3s ease;
  }}
  .callout-card .cc-sub {{
    font-size: 10.5px;
    font-weight: 700;
    color: var(--cream);
    margin-bottom: 3px;
  }}
  .callout-card .cc-detail {{
    font-size: 10px;
    line-height: 1.38;
    color: #CBD5E1;
  }}
  .callout-card .cc-lock-hint {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: 5px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--active-glow);
    text-transform: uppercase;
  }}

  /* Expanded state when hovered, locked, or Show-All */
  .callout-card.show-sub {{
    opacity: 0.94;
    width: 214px;
    background: rgba(20, 28, 43, 0.88);
    border-color: rgba(255, 195, 43, 0.72);
    transform: translateY(-50%) scale(1.0);
  }}
  .callout-card.show-sub .cc-body {{
    max-height: 36px;
    opacity: 1;
    margin-top: 4px;
    transform: translateY(0);
  }}
  .callout-card.show-sub .cc-detail,
  .callout-card.show-sub .cc-lock-hint {{ display: none; }}

  .callout-card:hover,
  .callout-card.active {{
    opacity: 1 !important;
    width: 244px !important;
    background: rgba(17, 24, 38, 0.95) !important;
    border: 1.5px solid var(--active-accent) !important;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.55), 0 0 18px rgba(255, 106, 19, 0.28);
    z-index: 26;
  }}
  .callout-card.side-L:hover, .callout-card.side-L.active {{
    transform: translateY(-50%) translateX(6px) scale(1.02) !important;
  }}
  .callout-card.side-R:hover, .callout-card.side-R.active {{
    transform: translateY(-50%) translateX(-6px) scale(1.02) !important;
  }}
  .callout-card:hover .cc-num,
  .callout-card.active .cc-num {{
    background: var(--active-accent);
    border-color: #fff;
    color: #fff;
  }}
  .callout-card:hover .cc-body,
  .callout-card.active .cc-body {{
    max-height: 150px !important;
    opacity: 1 !important;
    margin-top: 6px !important;
    transform: translateY(0) !important;
  }}
  .callout-card:hover .cc-detail,
  .callout-card.active .cc-detail,
  .callout-card:hover .cc-lock-hint,
  .callout-card.active .cc-lock-hint {{ display: block !important; }}

  /* Subtle dim for non-active cards while one is focused */
  #callout-layer.has-focus .callout-card:not(.active):not(:hover) {{
    opacity: 0.34;
  }}

  /* ── BOTTOM FROSTED-GLASS INTERACTIVE CONTROL DOCK ──────────── */
  .hero-dock {{
    position: absolute;
    left: 12px; right: 12px; bottom: 12px;
    z-index: 20;
    background: rgba(15, 21, 34, 0.84);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(148, 163, 184, 0.26);
    border-radius: 14px;
    padding: 8px 11px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  }}
  .dock-group {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }}
  .dock-lbl {{
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
    color: #94A3B8;
    text-transform: uppercase;
    margin-right: 2px;
  }}
  .seg-ctrl {{
    display: inline-flex;
    background: rgba(9, 13, 22, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 9px;
    padding: 2px;
    gap: 2px;
  }}
  .seg-btn {{
    background: transparent;
    border: none;
    color: #CBD5E1;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 9px;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.22s var(--ease-out-expo);
    white-space: nowrap;
  }}
  .seg-btn:hover {{ color: #fff; background: rgba(255, 255, 255, 0.07); }}
  .seg-btn.active {{
    background: var(--active-accent);
    color: #fff;
    box-shadow: 0 2px 10px rgba(255, 106, 19, 0.35);
  }}

  /* Colorway Swatch Buttons */
  .swatch-btn {{
    display: inline-flex;
    align-items: center;
    gap: 4.5px;
    background: rgba(255, 255, 255, 0.05);
    border: 1.5px solid rgba(148, 163, 184, 0.25);
    border-radius: 999px;
    padding: 3.5px 7.5px 3.5px 4.5px;
    color: #E2E8F0;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.24s var(--ease-out-expo);
    white-space: nowrap;
  }}
  .swatch-btn:hover {{ background: rgba(255, 255, 255, 0.12); transform: translateY(-1px); }}
  .swatch-btn.active {{
    border-color: #fff;
    background: rgba(255, 255, 255, 0.16);
    color: #fff;
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.22);
  }}
  .swatch-dot {{
    width: 14px; height: 14px;
    border-radius: 50%;
    border: 1.5px solid rgba(255, 255, 255, 0.65);
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
  }}
  .swatch-dot i {{
    position: absolute;
    bottom: 0; right: 0;
    width: 7px; height: 7px;
    border-top-left-radius: 4px;
  }}

  /* Icon / Action Buttons */
  .act-btn {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(148, 163, 184, 0.25);
    color: #E2E8F0;
    font-size: 10.5px;
    font-weight: 700;
    padding: 5px 9px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.22s var(--ease-out-expo);
    white-space: nowrap;
  }}
  .act-btn:hover {{ background: rgba(255, 255, 255, 0.16); color: #fff; }}
  .act-btn.active {{
    background: rgba(255, 195, 43, 0.2);
    border-color: var(--amber);
    color: var(--amber);
  }}

  /* ── CENTER BOTTOM MACRO CARD ───────────────────────────────── */
  .macro-grid {{
    display: grid;
    grid-template-columns: 0.96fr 1.04fr;
    gap: 12px;
    align-items: stretch;
  }}
  .macro-legend {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 5px;
  }}
  .macro-item {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 8px;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.22s var(--ease-out-expo);
  }}
  .macro-item:hover, .macro-item.active {{
    background: #F4F6FA;
    border-color: var(--active-accent);
    transform: translateX(3px);
  }}
  .macro-bar {{
    width: 5px; align-self: stretch; min-height: 28px;
    border-radius: 3px;
    flex-shrink: 0;
  }}
  .macro-t {{ font-size: 11.5px; font-weight: 800; color: var(--ink); line-height: 1.25; }}
  .macro-s {{ font-size: 10px; color: var(--muted); line-height: 1.3; margin-top: 1px; }}

  /* ── CARD 6 INTERACTIVE 4-COLORWAY SQUAD ────────────────────── */
  .squad-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    flex: 1;
  }}
  .squad-card {{
    background: #F7F8FA;
    border: 2px solid #E5E7EB;
    border-radius: 10px;
    padding: 6px 5px 7px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.25s var(--ease-out-expo);
    position: relative;
  }}
  .squad-card:hover {{
    transform: translateY(-2px);
    border-color: #94A3B8;
    box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
  }}
  .squad-card.active {{
    border-color: var(--active-accent);
    background: #FFFBF7;
    box-shadow: 0 6px 18px rgba(255, 106, 19, 0.16);
  }}
  .squad-card.active::after {{
    content: "3D ACTIVE";
    position: absolute;
    top: 4px; right: 4px;
    background: var(--active-accent);
    color: #fff;
    font-size: 8px;
    font-weight: 800;
    padding: 1.5px 5px;
    border-radius: 4px;
    letter-spacing: 0.04em;
  }}
  .squad-card img {{
    width: 100%;
    height: 112px;
    object-fit: contain;
    display: block;
  }}
  .squad-name {{
    font-size: 11px;
    font-weight: 800;
    color: var(--ink);
    margin-top: 4px;
  }}
  .squad-sub {{
    font-size: 9px;
    color: var(--muted);
    text-align: center;
    line-height: 1.2;
  }}
  .squad-swatches {{
    display: flex; gap: 3px; margin-top: 4px;
  }}
  .squad-swatches span {{
    width: 10px; height: 10px; border-radius: 50%;
    border: 1px solid rgba(0,0,0,0.18);
  }}

  /* ── FOOTER ─────────────────────────────────────────────────── */
  .poster-footer {{
    background: var(--hdr);
    border-top: 3px solid var(--active-accent);
    color: #D2DAE6;
    font-size: 11.5px;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .poster-footer .maturity {{ color: var(--amber); font-weight: 800; }}

  /* ── FULLSCREEN LIGHTBOX ────────────────────────────────────── */
  .lightbox {{
    position: fixed;
    inset: 0;
    background: rgba(9, 13, 22, 0.88);
    backdrop-filter: blur(12px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 28px;
    z-index: 999;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.25s ease, visibility 0.25s ease;
  }}
  .lightbox.open {{ opacity: 1; visibility: visible; }}
  .lightbox img {{
    max-width: 92vw;
    max-height: 82vh;
    border-radius: 12px;
    border: 2px solid rgba(255, 255, 255, 0.16);
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
    background: #fff;
  }}
  .lightbox-cap {{
    color: #F1F5F9;
    font-size: 13.5px;
    font-weight: 700;
    margin-top: 12px;
    text-align: center;
  }}
  .lightbox-close {{
    position: fixed;
    top: 18px; right: 24px;
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.28);
    background: rgba(20, 26, 38, 0.85);
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
  }}
  .lightbox-close:hover {{ background: var(--orange); }}

  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.5; transform: scale(0.8); }}
  }}
  @keyframes pin-ripple {{
    0% {{ transform: scale(0.95); opacity: 0.65; }}
    100% {{ transform: scale(1.75); opacity: 0; }}
  }}

  @media (max-width: 1320px) {{
    .poster-grid {{ grid-template-columns: 1fr; }}
    .hero-stage {{ min-height: 680px; }}
    .kpi-row {{ grid-template-columns: repeat(3, 1fr); width: 100%; }}
  }}
</style>
</head>
<body>

<!-- ── TOP BANNER ──────────────────────────────────────────────────────── -->
<header class="poster-header">
  <div class="hdr-left">
    <div class="hdr-badge"><span class="dot"></span>INTERACTIVE 3D HARDWARE CLOSEOUT · ASSEMBLY_FINISH_005</div>
    <h1 class="hdr-title">GOOSE V0.2 — MAX PRO BIPEDAL ROBOT GOOSE</h1>
    <div class="hdr-sub">Digital Hardware Closeout (assembly_finish_005) &nbsp;·&nbsp; 43-Collider SaiLab Virtual Goose &nbsp;·&nbsp; MicroDuck-Inspired Open-Source Platform</div>
  </div>
  <div class="kpi-row">
    <div class="kpi-pill"><div class="kpi-val">{total_mass_kg:.2f} kg</div><div class="kpi-lbl">005 TOTAL MASS</div></div>
    <div class="kpi-pill"><div class="kpi-val">{n_dof} DoF</div><div class="kpi-lbl">5 NECK · 1 BEAK · 12 LEG</div></div>
    <div class="kpi-pill"><div class="kpi-val">310 mm</div><div class="kpi-lbl">WIDENED HP STANCE</div></div>
    <div class="kpi-pill"><div class="kpi-val">{n_cad}+</div><div class="kpi-lbl">CAD PARTS RECONCILED</div></div>
    <div class="kpi-pill"><div class="kpi-val">{drc_viol}-DRC 6L</div><div class="kpi-lbl">{pcb_nets}/{pcb_nets} NETS ENV PCB</div></div>
    <div class="kpi-pill"><div class="kpi-val">{gpu_steps_s:,.0f} st/s</div><div class="kpi-lbl">32-ENV GPU MUJOCO</div></div>
  </div>
</header>

<!-- ── MAIN 3-COLUMN INTERACTIVE POSTER ────────────────────────────────── -->
<main class="poster-grid">

  <!-- ══ LEFT COLUMN (Cards 1, 2, 3) ═══════════════════════════════════ -->
  <section class="col">
    <!-- Card 1 -->
    <article class="card">
      <div class="card-hdr">1. HIP ARCHITECTURE (opt_b2_r2) &amp; CONVERGED FEA</div>
      <div class="card-body">
        <table class="scorecard">
          <thead>
            <tr><th>Gate / Metric</th><th>121 Static</th><th>4.67s Turn</th><th>A3 Loop</th><th>Gate</th></tr>
          </thead>
          <tbody>
            <tr><td>Struct Δ / 005 Mass</td><td>+{net_struct_g:.1f} g</td><td>{total_mass_kg:.3f} kg</td><td>Same MCI</td><td><span class="pass-pill">PASS</span></td></tr>
            <tr><td>C3D10 (116k DOF)</td><td>SJ={fine_sj:.4f}</td><td>ΔD=0.08%</td><td>ΔVM=1.40%</td><td><span class="pass-pill">PASS</span></td></tr>
            <tr><td>7075 Strength (503)</td><td>59.4 (8.5×)</td><td>48.7 (10.3×)</td><td>92.9 (5.4×)</td><td><span class="pass-pill">PASS</span></td></tr>
            <tr><td>Bolt Slip (11 Jts)</td><td>SF ≥ 6.65</td><td>SF ≥ 7.98</td><td>SF ≥ 5.73</td><td><span class="pass-pill">PASS</span></td></tr>
            <tr><td>Loaded Gap (-0.3)</td><td>≥ 1.187mm</td><td>1.110mm</td><td>1.012mm</td><td><span class="pass-pill">PASS</span></td></tr>
            <tr><td>Disp / 608 / SS</td><td>≤ 0.189mm</td><td>1.23 mrad</td><td>0v · 0.21s</td><td><span class="pass-pill">PASS</span></td></tr>
          </tbody>
        </table>
        <div class="note-line">• Billet Al 7075-T6 bridge + stator tie columns (6× C1 fillets R3–3.5 mm); K1/K2 zero modification.</div>
        <div class="fig-pair">
          <div class="fig-box" data-lightbox-cap="Fine C3D10 Converged Von Mises Stress Map (opt_b2_r2 · 115,875 DOFs · SF 5.4×)">
            <img src="{uri_vm}" alt="Converged FEA VM Stress" />
          </div>
          <div class="fig-box" data-lightbox-cap="Stage A3 Closed-Loop Single-Support Gait Verification (0.208 s · 0 torque/angle violations)">
            <img src="{uri_ss}" alt="Stage A3 Closed-Loop" />
          </div>
        </div>
      </div>
    </article>

    <!-- Card 2 -->
    <article class="card">
      <div class="card-hdr amber">2. ZERO-CUT FRONT SHELL YOKE RELIEF</div>
      <div class="card-body">
        <ul class="bullets">
          <li><strong>Unloaded Gap (body016_front):</strong><span>0.082 → {yoke_gap_after:.3f} mm (19.3×, 0/162 &lt; 1.5 mm)</span></li>
          <li><strong>Loaded Gap (-0.30 mm tol):</strong><span>1.012 mm (A3 SS) | 1.110 mm (Turn) | 1.187 mm (Static)</span></li>
          <li><strong>Shell Integrity &amp; Savings:</strong><span>PA12 wall 100% UNTOUCHED (2.12–2.27 mm) · -10.66 g/pair steel</span></li>
        </ul>
        <div class="fig-pair">
          <div class="fig-box" data-lightbox-cap="Zero-Cut Front Shell Yoke Relief — Unloaded & Loaded Clearance Envelope (162 poses)">
            <img src="{uri_a3_l}" alt="Yoke Relief Clearance Map" />
          </div>
          <div class="fig-box" data-lightbox-cap="Relieved Steel Yoke vs Untouched PA12 body016_front Cross-Section">
            <img src="{uri_a3_m}" alt="Yoke Relief Cross Section" />
          </div>
        </div>
      </div>
    </article>

    <!-- Card 3 (Animated Beak Grasp GIF) -->
    <article class="card">
      <div class="card-hdr">3. PARALLEL 4-BAR BEAK GRASP</div>
      <div class="card-body">
        <div class="beak-split">
          <div class="beak-specs">
            <div class="beak-item"><div class="bk-k">Neutral Beak Plane</div><div class="bk-v">z = {beak_z_m:.4f} m (fixed trap)</div></div>
            <div class="beak-item"><div class="bk-k">4-Bar Pin Residual</div><div class="bk-v">2.62×10⁻¹⁶ m (0 → 20° jaw)</div></div>
            <div class="beak-item"><div class="bk-k">Peak Actuator Torque</div><div class="bk-v">4.5 N·m (beak_input_rotor)</div></div>
            <div class="beak-item"><div class="bk-k">Grip Pad Material</div><div class="bk-v">85A TPU upper/lower cassettes</div></div>
            <div class="beak-item"><div class="bk-k">200 Hz 100 g Hold</div><div class="bk-v">PASS (1.0 s, Δz = -1.99 mm)</div></div>
            <div class="beak-item"><div class="bk-k">Mean Hold Forces</div><div class="bk-v">4.64 N upper / 7.03 N lower</div></div>
          </div>
          <div class="fig-box dark-bg" data-lightbox-cap="SaiLab 43-Collider Goose V0.2 — 200 Hz Parallel 4-Bar Beak Pick, Lift & Place Replay">
            <div class="live-badge"><span class="live-dot"></span>LIVE SIM · 4-BAR GRASP</div>
            <img src="{uri_gif_beak}" alt="Goose V0.2 4-Bar Beak Grasp Simulation GIF" />
            <div class="fig-cap">SaiLab 43-Collider · 200 Hz Beak Grasp / Lift / Place</div>
          </div>
        </div>
      </div>
    </article>
  </section>

  <!-- ══ CENTER COLUMN (Interactive 3D Hero Stage + Macro Cutaway) ═════ -->
  <section class="col">
    <div class="hero-stage" id="hero-stage">
      <canvas id="webgl-canvas"></canvas>

      <!-- Top HUD -->
      <div class="hero-hud-top">
        <div class="hero-mode-pill" id="hero-mode-pill">
          <span class="mode-dot"></span>
          <span id="hero-mode-text">WARM CREAM · SAGITTAL HALF-CUTAWAY</span>
        </div>
        <div class="hero-hint" id="hero-hint">拖拽空白处 360° 旋转 · 滚轮缩放 · 悬停/点击编号高亮部件</div>
      </div>

      <!-- Animated SVG Leader Lines -->
      <svg id="leader-svg" xmlns="http://www.w3.org/2000/svg"></svg>

      <!-- 3D Projected Hotspot Pins -->
      <div id="pin-layer"></div>

      <!-- 9 Smooth-Transition Side Callouts -->
      <div id="callout-layer"></div>

      <!-- Floating Zoom Rail (+ / 1.0x / -) -->
      <div class="zoom-rail" id="zoom-rail" aria-label="3D Viewport Zoom Controls">
        <button class="zoom-btn" id="btn-zoom-in" title="放大视图 (滚轮向上 / +)">+</button>
        <div class="zoom-readout" id="zoom-readout" title="当前缩放倍率">1.0×</div>
        <button class="zoom-btn" id="btn-zoom-out" title="缩小视图 (滚轮向下 / -)">−</button>
      </div>

      <!-- Bottom Frosted-Glass Control Dock -->
      <div class="hero-dock" id="hero-dock">
        <div class="dock-group">
          <span class="dock-lbl">左半壳</span>
          <div class="seg-ctrl" role="group" aria-label="Left Shell Cutaway Mode">
            <button class="seg-btn active" data-shell="cutaway" title="隐藏 Y<0 左半壳，展示内部机电架构">半剖</button>
            <button class="seg-btn" data-shell="full" title="显示完整双侧外观与腰线">完整外壳</button>
          </div>
        </div>

        <div class="dock-group">
          <span class="dock-lbl">主题色</span>
          <button class="swatch-btn active" data-color="cream" title="Warm Cream 奶油白">
            <span class="swatch-dot" style="background:#F2E5CF"><i style="background:#FF6A13"></i></span>Cream
          </button>
          <button class="swatch-btn" data-color="sky" title="Sky Blue 天空蓝 + 劳斯莱斯双腰线">
            <span class="swatch-dot" style="background:#6BC4E8"><i style="background:#FFB81C"></i></span>Sky
          </button>
          <button class="swatch-btn" data-color="graphite" title="Graphite 石墨灰 + 紫色双腰线">
            <span class="swatch-dot" style="background:#454952"><i style="background:#845EC2"></i></span>Graphite
          </button>
          <button class="swatch-btn" data-color="lavender" title="Lavender 薰衣草紫 + 冰蓝双腰线">
            <span class="swatch-dot" style="background:#B69CE2"><i style="background:#55C4E8"></i></span>Lavender
          </button>
        </div>

        <div class="dock-group">
          <button class="act-btn" id="btn-spin" title="开启/暂停 360° 自动旋转">⟳ 自转</button>
          <button class="act-btn" id="btn-hip" title="一键微距聚焦髋部机械与电子舱">◎ 髋部微距</button>
          <button class="act-btn" id="btn-all-labels" title="展开/收起全部 9 项标注">≡ 全部标注</button>
          <button class="act-btn" id="btn-reset" title="恢复标准 3/4 视角">↺ 重置</button>
        </div>
      </div>

      <!-- Loading Overlay -->
      <div class="loader-overlay" id="loader-overlay">
        <div class="spinner"></div>
        <div class="loader-txt" id="loader-txt">正在加载 Goose V0.2 (assembly_finish_005) 3D 剖视引擎…</div>
        <div class="loader-sub" id="loader-sub">离线内置 Three.js PBR + 2,529 件 CAD 双半壳模型</div>
      </div>
    </div>

    <!-- Bottom Center Macro Cutaway Card -->
    <article class="card">
      <div class="card-hdr amber">TORSO / HIP BAY MACRO CUTAWAY (assembly_finish_005) — 点击条目联动 3D 聚焦</div>
      <div class="card-body">
        <div class="macro-grid">
          <div class="fig-box dark-bg" style="min-height:190px" data-lightbox-cap="Goose V0.2 Torso & Hip Bay Cycles Macro Cutaway (144 spp · Upgraded P1/P2/U2D2/L1 Electronics + 005 CAD Hardware)">
            <img src="{uri_hip}" alt="Torso Hip Bay Cutaway Closeup" />
            <div class="fig-cap">Cycles 144 spp Macro · Click to Zoom</div>
          </div>
          <div class="macro-legend">
            <div class="macro-item" data-callout="6">
              <div class="macro-bar" style="background:#FFC32B"></div>
              <div><div class="macro-t">Al 7075-T6 Anchored Bridge (opt_b2_r2)</div><div class="macro-s">Warm billet aluminum · +141.2 g · 6× C1 fillets · 0.000 mm³ collision</div></div>
            </div>
            <div class="macro-item" data-callout="7">
              <div class="macro-bar" style="background:#8C9BAF"></div>
              <div><div class="macro-t">Relieved Steel Hip Yokes (smooth_005)</div><div class="macro-s">Brushed steel · 1.587 mm unloaded / ≥1.01 mm loaded gap · -10.66 g/pair</div></div>
            </div>
            <div class="macro-item" data-callout="4">
              <div class="macro-bar" style="background:#13733A"></div>
              <div><div class="macro-t">6L Emerald Avionics &amp; 24 V Mini-Board</div><div class="macro-s">0-DRC 106/106 Env PCB + 26-part OVP/Clamp mini-board (50k/50k MC)</div></div>
            </div>
            <div class="macro-item" data-callout="8">
              <div class="macro-bar" style="background:#FF6A13"></div>
              <div><div class="macro-t">Copper Coldplate &amp; Rear 1 A Fuse Pocket</div><div class="macro-s">5.81 W steady · 55°C no-next-brake lockout · 15/15 cover-clear +Y fuse</div></div>
            </div>
            <div class="macro-item" data-callout="5">
              <div class="macro-bar" style="background:#3C78C8"></div>
              <div><div class="macro-t">24 V Fan Protection &amp; 6S LiPo / K1–K2 Core</div><div class="macro-s">Zero mod to K1/K2/cassette · 1.385 mm min fixed gap · rear 1 A fuse pocket</div></div>
            </div>
          </div>
        </div>
      </div>
    </article>
  </section>

  <!-- ══ RIGHT COLUMN (Cards 4, 5, 6) ══════════════════════════════════ -->
  <section class="col">
    <!-- Card 4 (ENIG Green-Gold Top/Bottom PCB + Stackup + 50k MC) -->
    <article class="card">
      <div class="card-hdr">4. AVIONICS &amp; POWER CLOSEOUT (0-DRC + 24 V FAN)</div>
      <div class="card-body">
        <ul class="bullets">
          <li><strong>6-Layer Env PCB (fab_003):</strong><span>{drc_viol} DRC viol. · {pcb_nets}/{pcb_nets} nets · {pcb_fps} BOM/CPL · 419 drills</span></li>
          <li><strong>24 V Direct Fan OVP/Clamp:</strong><span>+{ovp_gap_mv:.1f} mV WC gap · {mc_pass:,}/{mc_trials:,} MC pass · 17.62 V floor</span></li>
          <li><strong>Serviceable 1 A Fuse Pocket:</strong><span>0.000 mm³ hit · 15/15 cover clear · 98.04 mm 6P tap · +{fan_delta_g:.1f} g</span></li>
        </ul>
        <div class="fig-pair pcb-split">
          <div class="fig-box" data-lightbox-cap="6-Layer ENIG Environment PCB — Top (L1 F.Cu) & Bottom (L6 B.Cu) + 0.8 mm FR4 Cross-Section Stackup (0 DRC · 419 PTH)">
            <img src="{uri_pcb}" alt="6-Layer ENIG Environment PCB" />
          </div>
          <div class="fig-box" data-lightbox-cap="24 V Direct Fan Protection — 50,000-Trial Monte Carlo OVP/Clamp Separation (50,000/50,000 PASS)">
            <img src="{uri_fan}" alt="50k Monte Carlo Separation" />
          </div>
        </div>
      </div>
    </article>

    <!-- Card 5 (Animated SaiLab Locomotion GIF + Drop GRF Chart) -->
    <article class="card">
      <div class="card-hdr amber">5. SAILAB VIRTUAL GOOSE (005/43 BUNDLE)</div>
      <div class="card-body">
        <ul class="bullets">
          <li><strong>43-Collider MuJoCo 3.15.0:</strong><span>22 bodies · 44 geoms · {total_mass_kg:.4f} kg (MCI err &lt; 10⁻¹⁶)</span></li>
          <li><strong>32-Env GPU Throughput:</strong><span>{gpu_steps_s:,.1f} world-steps/s (p95 = {gpu_p95_ms:.2f} ms, 0 NaNs)</span></li>
          <li><strong>Determinism &amp; Cold Gates:</strong><span>2+1 PPO save/resume bit-exact (SHA match) · 8/8 gates PASS</span></li>
        </ul>
        <div class="fig-pair">
          <div class="fig-box dark-bg" data-lightbox-cap="SaiLab 43-Collider Goose V0.2 — Steady World-Dolly Replay of 200 Hz Bipedal Run (p350_43 · 4.15 m · 0.56 m/s)">
            <div class="live-badge"><span class="live-dot"></span>LIVE SIM · 43-COLLIDER RUN</div>
            <img src="{uri_gif_loco}" alt="SaiLab Goose V0.2 Steady Locomotion GIF" />
            <div class="fig-cap">SaiLab 43-Collider · 200 Hz Steady Run (0.56 m/s)</div>
          </div>
          <div class="fig-box" data-lightbox-cap="43-Collider Drop Ground Reaction Force & 100 g 200 Hz Grasp Contact Telemetry">
            <img src="{uri_grf}" alt="Drop GRF & Grasp Force" />
          </div>
        </div>
      </div>
    </article>

    <!-- Card 6 (Interactive 4-Colorway Squad Switcher) -->
    <article class="card">
      <div class="card-hdr">6. MICRODUCK-INSPIRED 4-COLORWAY SQUAD — 点击切换 3D 配色</div>
      <div class="card-body">
        <div class="squad-grid" id="squad-grid">
          <div class="squad-card" data-color="sky">
            <img src="{theme_thumbs['sky']}" alt="Sky Blue Goose" />
            <div class="squad-name">Sky Blue</div>
            <div class="squad-sub">Cyan · RR Amber Line</div>
            <div class="squad-swatches"><span style="background:#6BC4E8"></span><span style="background:#FF6A13"></span><span style="background:#FFB81C"></span></div>
          </div>
          <div class="squad-card" data-color="graphite">
            <img src="{theme_thumbs['graphite']}" alt="Graphite Goose" />
            <div class="squad-name">Graphite</div>
            <div class="squad-sub">Slate · RR Violet Line</div>
            <div class="squad-swatches"><span style="background:#454952"></span><span style="background:#F5C724"></span><span style="background:#845EC2"></span></div>
          </div>
          <div class="squad-card active" data-color="cream">
            <img src="{theme_thumbs['cream']}" alt="Warm Cream Goose" />
            <div class="squad-name">Warm Cream</div>
            <div class="squad-sub">Flagship Pure Ivory</div>
            <div class="squad-swatches"><span style="background:#F2E5CF"></span><span style="background:#FF6A13"></span><span style="background:#FFC32B"></span></div>
          </div>
          <div class="squad-card" data-color="lavender">
            <img src="{theme_thumbs['lavender']}" alt="Lavender Goose" />
            <div class="squad-name">Lavender</div>
            <div class="squad-sub">Violet · RR Cyan Line</div>
            <div class="squad-swatches"><span style="background:#B69CE2"></span><span style="background:#F5C724"></span><span style="background:#55C4E8"></span></div>
          </div>
        </div>
      </div>
    </article>
  </section>
</main>

<!-- ── FOOTER ──────────────────────────────────────────────────────────── -->
<footer class="poster-footer">
  <div>github.com/sgyli7/Sai_Rotbots &nbsp;·&nbsp; robots/goose_v0_2 &nbsp;·&nbsp; Interactive Single-HTML Flagship Poster (assembly_finish_005) · All metrics verified from cold receipts</div>
  <div class="maturity">Digital Design Frozen (Step 1 PASS) &nbsp;|&nbsp; Physical Bench &amp; Procurement (Step 2 Deferred)</div>
</footer>

<!-- ── FULLSCREEN LIGHTBOX ─────────────────────────────────────────────── -->
<div class="lightbox" id="lightbox" role="dialog" aria-modal="true">
  <button class="lightbox-close" id="lightbox-close" aria-label="Close">×</button>
  <img id="lightbox-img" src="" alt="" />
  <div class="lightbox-cap" id="lightbox-cap"></div>
</div>

<!-- ── EMBEDDED OFFLINE GZIPPED PAYLOADS (Three.js r170 + 005 Dual-Half GLB) -->
<script type="text/plain" id="gz-three">{b64_three}</script>
<script type="text/plain" id="gz-bgu">{b64_bgu}</script>
<script type="text/plain" id="gz-gltf">{b64_gltf}</script>
<script type="text/plain" id="gz-orbit">{b64_orbit}</script>
<script type="text/plain" id="gz-room">{b64_room}</script>
<script type="text/plain" id="gz-glb">{b64_glb}</script>

<script>
(() => {{
  const CALLOUTS = {json.dumps(callouts_data, ensure_ascii=False)};
  const COLORWAYS = {json.dumps(colorways_js, ensure_ascii=False)};

  // ── Lightbox wiring ──────────────────────────────────────────────────
  const lb = document.getElementById('lightbox');
  const lbImg = document.getElementById('lightbox-img');
  const lbCap = document.getElementById('lightbox-cap');
  document.querySelectorAll('.fig-box').forEach(box => {{
    box.addEventListener('click', () => {{
      const img = box.querySelector('img');
      if (!img) return;
      lbImg.src = img.src;
      lbCap.textContent = box.dataset.lightboxCap || img.alt || '';
      lb.classList.add('open');
    }});
  }});
  const closeLb = () => lb.classList.remove('open');
  document.getElementById('lightbox-close').addEventListener('click', closeLb);
  lb.addEventListener('click', e => {{ if (e.target === lb) closeLb(); }});
  window.addEventListener('keydown', e => {{
    if (e.key === 'Escape') {{
      closeLb();
      if (window.__gooseUnlock) window.__gooseUnlock();
    }}
  }});

  // ── Gzip Base64 Decompression helper (100% browser-native, zero CDN) ─
  async function gunzipBase64ToBytes(b64) {{
    const bin = atob(b64.trim());
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    if (typeof DecompressionStream === 'undefined') {{
      throw new Error('Browser does not support DecompressionStream("gzip"). Please open in modern Chrome, Edge, Firefox, or Safari.');
    }}
    const ds = new DecompressionStream('gzip');
    const stream = new Blob([bytes]).stream().pipeThrough(ds);
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab);
  }}

  async function gunzipBase64ToText(b64) {{
    const bytes = await gunzipBase64ToBytes(b64);
    return new TextDecoder('utf-8').decode(bytes);
  }}

  async function boot3D() {{
    const loaderOverlay = document.getElementById('loader-overlay');
    const loaderTxt = document.getElementById('loader-txt');
    const loaderSub = document.getElementById('loader-sub');

    try {{
      loaderTxt.textContent = '正在解压内置 Three.js r170 PBR 引擎…';
      const [threeSrc, bguSrc, gltfSrc, orbitSrc, roomSrc] = await Promise.all([
        gunzipBase64ToText(document.getElementById('gz-three').textContent),
        gunzipBase64ToText(document.getElementById('gz-bgu').textContent),
        gunzipBase64ToText(document.getElementById('gz-gltf').textContent),
        gunzipBase64ToText(document.getElementById('gz-orbit').textContent),
        gunzipBase64ToText(document.getElementById('gz-room').textContent),
      ]);

      const mkUrl = src => URL.createObjectURL(new Blob([src], {{ type: 'application/javascript' }}));
      const threeUrl = mkUrl(threeSrc);
      const bguUrl = mkUrl(bguSrc.replace(/from\\s+['"]three['"]/g, `from '${{threeUrl}}'`));
      const gltfUrl = mkUrl(
        gltfSrc
          .replace(/from\\s+['"]three['"]/g, `from '${{threeUrl}}'`)
          .replace(/from\\s+['"]\\.\\.\\/utils\\/BufferGeometryUtils\\.js['"]/g, `from '${{bguUrl}}'`)
      );
      const orbitUrl = mkUrl(orbitSrc.replace(/from\\s+['"]three['"]/g, `from '${{threeUrl}}'`));
      const roomUrl = mkUrl(roomSrc.replace(/from\\s+['"]three['"]/g, `from '${{threeUrl}}'`));

      const [THREE, {{ GLTFLoader }}, {{ OrbitControls }}, {{ RoomEnvironment }}] = await Promise.all([
        import(threeUrl),
        import(gltfUrl),
        import(orbitUrl),
        import(roomUrl),
      ]);

      loaderTxt.textContent = '正在解压 Goose V0.2 双半壳 CAD 模型…';
      const glbBytes = await gunzipBase64ToBytes(document.getElementById('gz-glb').textContent);

      // ── Renderer & Scene Setup ───────────────────────────────────────
      const stage = document.getElementById('hero-stage');
      const canvas = document.getElementById('webgl-canvas');
      const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      const scene = new THREE.Scene();
      const pmrem = new THREE.PMREMGenerator(renderer);
      scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      scene.environmentIntensity = 0.72;

      // Exact Cycles cutaway hero camera mapped from Blender Z-up -> Three.js Y-up:
      // Blender (1.40, -0.78, 0.56) -> Three.js (1.40, 0.56, 0.78), target (-0.015, 0.325, -0.002)
      const DEFAULT_CAM_POS = new THREE.Vector3(1.18, 0.52, 0.74);
      const DEFAULT_CAM_TGT = new THREE.Vector3(-0.012, 0.335, 0.002);
      const HIP_CAM_POS = new THREE.Vector3(0.42, 0.42, 0.48);
      const HIP_CAM_TGT = new THREE.Vector3(-0.030, 0.345, 0.025);

      const camera = new THREE.PerspectiveCamera(34, stage.clientWidth / stage.clientHeight, 0.02, 20);
      camera.position.copy(DEFAULT_CAM_POS);

      const controls = new OrbitControls(camera, canvas);
      controls.target.copy(DEFAULT_CAM_TGT);
      controls.enableDamping = true;
      controls.dampingFactor = 0.068;
      controls.rotateSpeed = 0.78;
      controls.zoomSpeed = 1.25;
      controls.panSpeed = 0.55;
      controls.enableZoom = true;
      controls.minDistance = 0.22;
      controls.maxDistance = 3.20;
      controls.minPolarAngle = 0.14;
      controls.maxPolarAngle = Math.PI - 0.12;
      controls.autoRotate = false;
      controls.autoRotateSpeed = 1.35;
      controls.update();
      const DEFAULT_DIST = DEFAULT_CAM_POS.distanceTo(DEFAULT_CAM_TGT);

      // ── Studio Lighting Rig (mirroring Cycles Dark Cutaway) ──────────
      const hemi = new THREE.HemisphereLight(0xdceaff, 0x161d2b, 0.52);
      scene.add(hemi);

      const keyLight = new THREE.DirectionalLight(0xfffdf8, 2.25);
      keyLight.position.set(1.5, 1.8, 1.35);
      keyLight.castShadow = true;
      keyLight.shadow.mapSize.set(1024, 1024);
      keyLight.shadow.camera.near = 0.4;
      keyLight.shadow.camera.far = 5.0;
      keyLight.shadow.camera.left = -0.65;
      keyLight.shadow.camera.right = 0.65;
      keyLight.shadow.camera.top = 0.85;
      keyLight.shadow.camera.bottom = -0.45;
      keyLight.shadow.bias = -0.0005;
      scene.add(keyLight);

      const fillCutaway = new THREE.DirectionalLight(0xd8ecff, 1.15);
      fillCutaway.position.set(0.45, 0.65, 1.65);
      scene.add(fillCutaway);

      const rimCyan = new THREE.DirectionalLight(0x6ad0ff, 1.35);
      rimCyan.position.set(-1.35, 1.25, 0.95);
      scene.add(rimCyan);

      const rimViolet = new THREE.DirectionalLight(0xb084ff, 1.05);
      rimViolet.position.set(-1.05, 1.25, -1.25);
      scene.add(rimViolet);

      const hipAccent = new THREE.PointLight(0xfff2dc, 0.55, 1.2, 2.0);
      hipAccent.position.set(0.18, 0.48, 0.42);
      scene.add(hipAccent);

      // Subtle grounded shadow floor + precision turntable ring at foot plane y = -0.0155
      const shadowFloor = new THREE.Mesh(
        new THREE.CircleGeometry(0.95, 64),
        new THREE.ShadowMaterial({{ opacity: 0.42 }})
      );
      shadowFloor.rotation.x = -Math.PI / 2;
      shadowFloor.position.y = -0.0158;
      shadowFloor.receiveShadow = true;
      scene.add(shadowFloor);

      const ringGeo = new THREE.RingGeometry(0.285, 0.292, 96);
      const ringMat = new THREE.MeshBasicMaterial({{ color: 0xffc32b, transparent: true, opacity: 0.16, side: THREE.DoubleSide }});
      const floorRing = new THREE.Mesh(ringGeo, ringMat);
      floorRing.rotation.x = -Math.PI / 2;
      floorRing.position.y = -0.0152;
      scene.add(floorRing);

      // Subtle 3D beacon sphere + halo ring for hovered/selected subsystem anchor
      const beaconGroup = new THREE.Group();
      beaconGroup.visible = false;
      const beaconCore = new THREE.Mesh(
        new THREE.SphereGeometry(0.008, 20, 20),
        new THREE.MeshBasicMaterial({{ color: 0xff6a13, depthTest: false, transparent: true, opacity: 0.95 }})
      );
      beaconCore.renderOrder = 999;
      const beaconRing = new THREE.Mesh(
        new THREE.RingGeometry(0.014, 0.019, 32),
        new THREE.MeshBasicMaterial({{ color: 0xffc32b, side: THREE.DoubleSide, depthTest: false, transparent: true, opacity: 0.85 }})
      );
      beaconRing.renderOrder = 998;
      beaconGroup.add(beaconCore, beaconRing);
      scene.add(beaconGroup);

      // ── Rolls-Royce Twin Torso Coachline Shader Hook ─────────────────
      const coachUniforms = {{
        uCoachEnable: {{ value: 0.0 }},
        uCoachColor: {{ value: new THREE.Color('#FFB81C') }},
      }};

      function patchCoachlineShader(mat) {{
        mat.onBeforeCompile = (shader) => {{
          shader.uniforms.uCoachEnable = coachUniforms.uCoachEnable;
          shader.uniforms.uCoachColor = coachUniforms.uCoachColor;
          shader.vertexShader = shader.vertexShader
            .replace(
              '#include <common>',
              `#include <common>
              varying vec3 vCoachWorldPos;
              varying vec3 vCoachWorldNorm;`
            )
            .replace(
              '#include <begin_vertex>',
              `#include <begin_vertex>
              vec4 cwp = modelMatrix * vec4(transformed, 1.0);
              vCoachWorldPos = cwp.xyz;
              vCoachWorldNorm = normalize(mat3(modelMatrix) * objectNormal);`
            );
          shader.fragmentShader = shader.fragmentShader
            .replace(
              '#include <common>',
              `#include <common>
              uniform float uCoachEnable;
              uniform vec3 uCoachColor;
              varying vec3 vCoachWorldPos;
              varying vec3 vCoachWorldNorm;`
            )
            .replace(
              '#include <color_fragment>',
              `#include <color_fragment>
              if (uCoachEnable > 0.5) {{
                // Exact Blender Z-up -> Three.js Y-up mapping: x_b = x, z_b = y
                vec3 toOut = vCoachWorldPos - vec3(-0.05, 0.35, 0.0);
                float extMask = smoothstep(0.01, 0.03, dot(normalize(vCoachWorldNorm), toOut));
                float zLine = 0.391 - 0.015 * vCoachWorldPos.x;
                float b1 = (1.0 - smoothstep(0.0019, 0.0023, abs(vCoachWorldPos.y - zLine)))
                         * smoothstep(-0.276, -0.264, vCoachWorldPos.x);
                float b2 = (1.0 - smoothstep(0.00075, 0.0011, abs(vCoachWorldPos.y - (zLine - 0.0052))))
                         * smoothstep(-0.242, -0.230, vCoachWorldPos.x);
                float cf = max(b1, b2) * extMask;
                diffuseColor.rgb = mix(diffuseColor.rgb, uCoachColor, cf);
              }}`
            );
        }};
        mat.customProgramCacheKey = () => 'goose005_rr_coachline_v1';
      }}

      // ── Load GLB & Categorize All Meshes ─────────────────────────────
      const loader = new GLTFLoader();
      const gltf = await new Promise((resolve, reject) => {{
        loader.parse(glbBytes.buffer, '', resolve, reject);
      }});

      const robotRoot = gltf.scene;
      scene.add(robotRoot);

      const leftExtMeshes = [];
      const hlGroups = {{}};
      const roleMeshes = {{
        shell: [],
        torso_coach: [],
        accent: [],
        eye_ring: [],
        sole_accent: [],
        dark_mechanics: [],
      }};
      const pickableMeshes = [];

      const HL_KEYS = CALLOUTS.map(c => c.group);

      function findBatchName(obj) {{
        let cur = obj;
        let found = '';
        while (cur && cur !== robotRoot) {{
          if (cur.name && /^(EXT_LEFT_|EXT_RIGHT_|HL[1-9]_|INT_CHASSIS)/.test(cur.name)) {{
            found = cur.name; // keep walking up to get the parent group name if multi-material split
          }}
          cur = cur.parent;
        }}
        return found || obj.name || '';
      }}

      robotRoot.traverse(child => {{
        if (!child.isMesh) return;
        const batch = findBatchName(child);
        const origMatName = (child.material && child.material.name) ? child.material.name : '';
        child.material = child.material.clone();
        const m = child.material;
        m.needsUpdate = true;

        child.castShadow = true;
        child.receiveShadow = true;
        child.userData.batch = batch;
        child.userData.origMatName = origMatName;
        child.userData.baseRoughness = m.roughness;
        child.userData.baseEmissive = m.emissive ? m.emissive.clone() : new THREE.Color(0x000000);
        child.userData.baseEmissiveIntensity = m.emissiveIntensity || 0;

        if (batch.startsWith('EXT_LEFT_')) {{
          leftExtMeshes.push(child);
          child.visible = false; // start cleanly in Half-Cutaway mode
        }}

        // Classify finish material role for live 4-colorway switching
        if (origMatName.startsWith('Ext_WarmCream')) {{
          if (batch.includes('TORSO_COACH')) {{
            patchCoachlineShader(m);
            roleMeshes.torso_coach.push(child);
          }} else {{
            roleMeshes.shell.push(child);
          }}
        }} else if (origMatName.startsWith('Ext_TangerineOrange')) {{
          roleMeshes.accent.push(child);
        }} else if (origMatName.startsWith('Ext_GoldenAmber')) {{
          if (batch.includes('EYE_RING')) roleMeshes.eye_ring.push(child);
          else roleMeshes.sole_accent.push(child);
        }} else if (origMatName.startsWith('Ext_DarkCharcoal') || origMatName.startsWith('Ext_Faceplate')) {{
          roleMeshes.dark_mechanics.push(child);
        }}

        // Map subsystem highlight groups HL1..HL9 reliably even across glTF multi-material primitives (_1, _2...)
        const hlKey = HL_KEYS.find(k => batch === k || batch.startsWith(k + '_') || batch.startsWith(k + '.'));
        if (hlKey) {{
          if (!hlGroups[hlKey]) hlGroups[hlKey] = [];
          hlGroups[hlKey].push(child);
          child.userData.hlGroup = hlKey;
          pickableMeshes.push(child);
        }}
        // Also let clicking/hovering the eye bezel highlight HL1_OPTICS
        if (batch.includes('EYE_RING') || batch.includes('GLASS')) {{
          if (!hlGroups['HL1_OPTICS']) hlGroups['HL1_OPTICS'] = [];
          hlGroups['HL1_OPTICS'].push(child);
          child.userData.hlGroup = 'HL1_OPTICS';
          pickableMeshes.push(child);
        }}
      }});

      // ── State Variables ──────────────────────────────────────────────
      let shellMode = 'cutaway'; // 'cutaway' | 'full'
      let currentLeftOpacity = 0.0;
      let targetLeftOpacity = 0.0;
      let activeColorway = 'cream';
      let showAllLabels = false;
      let hoveredId = null;
      let lockedId = null;
      let isDragging = false;

      // Smooth camera transition & zoom helpers
      let camAnim = null;
      function flyCamera(toPos, toTarget, durationMs = 760) {{
        camAnim = {{
          t0: performance.now(),
          dur: durationMs,
          fromPos: camera.position.clone(),
          toPos: new THREE.Vector3(...toPos),
          fromTgt: controls.target.clone(),
          toTgt: new THREE.Vector3(...toTarget),
        }};
      }}

      function zoomBy(scaleFactor, durationMs = 240) {{
        const offset = camera.position.clone().sub(controls.target);
        const curDist = offset.length();
        const nextDist = Math.max(controls.minDistance, Math.min(controls.maxDistance, curDist * scaleFactor));
        offset.setLength(nextDist);
        const dest = controls.target.clone().add(offset);
        flyCamera([dest.x, dest.y, dest.z], [controls.target.x, controls.target.y, controls.target.z], durationMs);
      }}

      function updateModeBanner() {{
        const cw = COLORWAYS[activeColorway];
        const modeTxt = shellMode === 'cutaway' ? 'SAGITTAL HALF-CUTAWAY' : 'FULL EXTERIOR';
        document.getElementById('hero-mode-text').textContent = `${{cw.name.toUpperCase()}} · ${{modeTxt}}`;
      }}

      function setShellMode(mode) {{
        shellMode = (mode === 'full') ? 'full' : 'cutaway';
        targetLeftOpacity = shellMode === 'cutaway' ? 0.0 : 1.0;
        document.querySelectorAll('.seg-btn[data-shell]').forEach(b => b.classList.toggle('active', b.dataset.shell === shellMode));
        updateModeBanner();
      }}

      function applyColorway(cid) {{
        const cw = COLORWAYS[cid];
        if (!cw) return;
        activeColorway = cid;
        const setCol = (list, hex, rough) => {{
          const c = new THREE.Color(hex);
          list.forEach(mesh => {{
            mesh.material.color.copy(c);
            if (rough !== undefined) {{
              mesh.userData.baseRoughness = rough;
              if (!mesh.userData.batch.startsWith('EXT_LEFT_') || shellMode === 'full') {{
                mesh.material.roughness = rough;
              }}
            }}
          }});
        }};
        setCol(roleMeshes.shell, cw.shell, cw.shellRough);
        setCol(roleMeshes.torso_coach, cw.shell, cw.shellRough);
        setCol(roleMeshes.accent, cw.accent, 0.34);
        setCol(roleMeshes.eye_ring, cw.eyeRing, 0.32);
        setCol(roleMeshes.sole_accent, cw.soleAccent, 0.32);
        setCol(roleMeshes.dark_mechanics, cw.dark, 0.40);

        if (cw.coachline) {{
          coachUniforms.uCoachEnable.value = 1.0;
          coachUniforms.uCoachColor.value.set(cw.coachline);
        }} else {{
          coachUniforms.uCoachEnable.value = 0.0;
        }}

        document.documentElement.style.setProperty('--active-accent', cw.uiAccent);
        document.documentElement.style.setProperty('--active-glow', cw.uiAmber);
        ringMat.color.set(cw.uiAmber);
        beaconCore.material.color.set(cw.uiAccent);
        beaconRing.material.color.set(cw.uiAmber);

        document.querySelectorAll('.swatch-btn[data-color]').forEach(b => b.classList.toggle('active', b.dataset.color === cid));
        document.querySelectorAll('.squad-card[data-color]').forEach(c => c.classList.toggle('active', c.dataset.color === cid));
        updateModeBanner();
      }}

      // ── Build 9 Interactive Hotspot Pins, Callout Cards & SVG Leaders ─
      const pinLayer = document.getElementById('pin-layer');
      const calloutLayer = document.getElementById('callout-layer');
      const leaderSvg = document.getElementById('leader-svg');
      const SVG_NS = 'http://www.w3.org/2000/svg';

      const uiItems = new Map();
      CALLOUTS.forEach(c => {{
        // 3D Hotspot Pin
        const pin = document.createElement('button');
        pin.className = 'hotspot-pin';
        pin.textContent = String(c.id);
        pin.setAttribute('aria-label', c.title);
        pinLayer.appendChild(pin);

        // Smooth-Transition Side Callout Card
        const card = document.createElement('div');
        card.className = `callout-card side-${{c.side}}`;
        card.style.top = `${{c.slotPct}}%`;
        card.innerHTML = `
          <div class="cc-head">
            <span class="cc-num">${{c.id}}</span>
            <span class="cc-title cc-t-short">${{c.short}}</span>
            <span class="cc-title cc-t-full">${{c.title.replace(/^\\d+\\.\\s*/, '')}}</span>
          </div>
          <div class="cc-body">
            <div class="cc-sub">${{c.sub}}</div>
            <div class="cc-detail">${{c.detail}}</div>
            <div class="cc-lock-hint">点击聚焦 3D 区域 · Click to Focus</div>
          </div>
        `;
        calloutLayer.appendChild(card);

        // SVG Leader Polyline Group
        const g = document.createElementNS(SVG_NS, 'g');
        g.setAttribute('class', 'leader-group');
        const halo = document.createElementNS(SVG_NS, 'polyline');
        halo.setAttribute('class', 'leader-path-halo');
        const line = document.createElementNS(SVG_NS, 'polyline');
        line.setAttribute('class', 'leader-path');
        g.appendChild(halo);
        g.appendChild(line);
        leaderSvg.appendChild(g);

        const onEnter = () => {{
          if (isDragging) return;
          hoveredId = c.id;
          syncHighlightUI();
        }};
        const onLeave = () => {{
          if (hoveredId === c.id) hoveredId = null;
          syncHighlightUI();
        }};
        const onClick = (ev) => {{
          ev.stopPropagation();
          if (lockedId === c.id) {{
            lockedId = null;
          }} else {{
            lockedId = c.id;
            if (c.internal && shellMode === 'full') setShellMode('cutaway');
            controls.autoRotate = false;
            document.getElementById('btn-spin').classList.remove('active');
            flyCamera(c.focusCam, c.focusTarget, 780);
          }}
          syncHighlightUI();
        }};

        pin.addEventListener('mouseenter', onEnter);
        pin.addEventListener('mouseleave', onLeave);
        pin.addEventListener('click', onClick);
        card.addEventListener('mouseenter', onEnter);
        card.addEventListener('mouseleave', onLeave);
        card.addEventListener('click', onClick);

        uiItems.set(c.id, {{
          data: c,
          anchorVec: new THREE.Vector3(...c.anchor),
          pin,
          card,
          svgGroup: g,
          halo,
          line,
        }});
      }});

      function getEffectiveId() {{
        return hoveredId !== null ? hoveredId : lockedId;
      }}

      function syncHighlightUI() {{
        const effId = getEffectiveId();
        calloutLayer.classList.toggle('has-focus', effId !== null && !showAllLabels);
        uiItems.forEach((item, id) => {{
          const isAct = id === effId;
          item.pin.classList.toggle('visible', isAct || showAllLabels);
          item.pin.classList.toggle('active', isAct);
          item.card.classList.toggle('active', isAct);
          item.card.classList.toggle('show-sub', showAllLabels && !isAct);
          item.svgGroup.classList.toggle('visible', isAct || showAllLabels);
          item.svgGroup.classList.toggle('active', isAct);
          const hint = item.card.querySelector('.cc-lock-hint');
          if (hint) {{
            hint.textContent = (lockedId === id) ? '已锁定聚焦 · 再次点击解锁' : '点击聚焦 3D 区域 · Click to Focus';
          }}
        }});
        document.querySelectorAll('.macro-item[data-callout]').forEach(el => {{
          el.classList.toggle('active', Number(el.dataset.callout) === effId);
        }});

        if (effId !== null) {{
          const targetItem = uiItems.get(effId);
          beaconGroup.visible = true;
          beaconGroup.position.copy(targetItem.anchorVec);
        }} else {{
          beaconGroup.visible = false;
        }}
      }}

      window.__gooseUnlock = () => {{
        lockedId = null;
        hoveredId = null;
        syncHighlightUI();
      }};

      // ── Wire Macro Legend Items to 3D Highlight & Focus ──────────────
      document.querySelectorAll('.macro-item[data-callout]').forEach(el => {{
        const cid = Number(el.dataset.callout);
        el.addEventListener('mouseenter', () => {{ hoveredId = cid; syncHighlightUI(); }});
        el.addEventListener('mouseleave', () => {{ if (hoveredId === cid) hoveredId = null; syncHighlightUI(); }});
        el.addEventListener('click', () => {{
          const item = uiItems.get(cid);
          if (!item) return;
          lockedId = cid;
          if (item.data.internal && shellMode === 'full') setShellMode('cutaway');
          controls.autoRotate = false;
          document.getElementById('btn-spin').classList.remove('active');
          flyCamera(item.data.focusCam, item.data.focusTarget, 780);
          syncHighlightUI();
        }});
      }});

      // ── Wire Bottom Control Dock, Zoom Rail & Card 6 Squad Buttons ───
      document.querySelectorAll('.seg-btn[data-shell]').forEach(btn => {{
        btn.addEventListener('click', () => setShellMode(btn.dataset.shell));
      }});

      document.getElementById('btn-zoom-in').addEventListener('click', () => zoomBy(0.78));
      document.getElementById('btn-zoom-out').addEventListener('click', () => zoomBy(1.28));
      stage.addEventListener('wheel', e => {{
        if (e.target === canvas || e.target.closest('.hero-dock')) return;
        e.preventDefault();
        zoomBy(e.deltaY > 0 ? 1.12 : 0.89, 140);
      }}, {{ passive: false }});
      window.addEventListener('keydown', e => {{
        if (lb.classList.contains('open')) return;
        if (e.key === '+' || e.key === '=') zoomBy(0.80);
        else if (e.key === '-' || e.key === '_') zoomBy(1.25);
      }});

      document.querySelectorAll('.swatch-btn[data-color], .squad-card[data-color]').forEach(btn => {{
        btn.addEventListener('click', () => applyColorway(btn.dataset.color));
      }});

      const btnSpin = document.getElementById('btn-spin');
      btnSpin.addEventListener('click', () => {{
        controls.autoRotate = !controls.autoRotate;
        btnSpin.classList.toggle('active', controls.autoRotate);
      }});

      document.getElementById('btn-hip').addEventListener('click', () => {{
        if (shellMode === 'full') setShellMode('cutaway');
        controls.autoRotate = false;
        btnSpin.classList.remove('active');
        lockedId = 6;
        flyCamera([HIP_CAM_POS.x, HIP_CAM_POS.y, HIP_CAM_POS.z], [HIP_CAM_TGT.x, HIP_CAM_TGT.y, HIP_CAM_TGT.z], 760);
        syncHighlightUI();
      }});

      const btnAll = document.getElementById('btn-all-labels');
      btnAll.addEventListener('click', () => {{
        showAllLabels = !showAllLabels;
        btnAll.classList.toggle('active', showAllLabels);
        syncHighlightUI();
      }});

      document.getElementById('btn-reset').addEventListener('click', () => {{
        lockedId = null;
        hoveredId = null;
        controls.autoRotate = false;
        btnSpin.classList.remove('active');
        flyCamera([DEFAULT_CAM_POS.x, DEFAULT_CAM_POS.y, DEFAULT_CAM_POS.z], [DEFAULT_CAM_TGT.x, DEFAULT_CAM_TGT.y, DEFAULT_CAM_TGT.z], 760);
        syncHighlightUI();
      }});

      // ── Pointer & Raycaster Handling (360° Drag vs Direct Mesh Hover) ─
      const raycaster = new THREE.Raycaster();
      const pointerNdc = new THREE.Vector2();
      let downXY = null;
      let rayThrottle = 0;

      controls.addEventListener('start', () => {{
        isDragging = true;
        camAnim = null;
        document.getElementById('hero-hint').classList.add('dimmed');
      }});
      controls.addEventListener('end', () => {{
        setTimeout(() => {{ isDragging = false; }}, 60);
      }});

      canvas.addEventListener('pointerdown', e => {{
        downXY = [e.clientX, e.clientY];
      }});
      canvas.addEventListener('pointerup', e => {{
        if (!downXY) return;
        const dist = Math.hypot(e.clientX - downXY[0], e.clientY - downXY[1]);
        downXY = null;
        if (dist < 5) {{
          // Pure click on canvas: raycast subsystem or unlock if empty space
          const rect = canvas.getBoundingClientRect();
          pointerNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
          pointerNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
          raycaster.setFromCamera(pointerNdc, camera);
          const hits = raycaster.intersectObjects(pickableMeshes, false).filter(h => h.object.visible);
          if (hits.length > 0 && hits[0].object.userData.hlGroup) {{
            const g = hits[0].object.userData.hlGroup;
            const found = CALLOUTS.find(c => c.group === g);
            if (found) {{
              lockedId = (lockedId === found.id) ? null : found.id;
              syncHighlightUI();
              return;
            }}
          }}
          if (lockedId !== null) {{
            lockedId = null;
            syncHighlightUI();
          }}
        }}
      }});

      canvas.addEventListener('pointermove', e => {{
        if (isDragging || e.buttons !== 0) return;
        const now = performance.now();
        if (now - rayThrottle < 45) return;
        rayThrottle = now;
        const rect = canvas.getBoundingClientRect();
        pointerNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        pointerNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(pointerNdc, camera);
        const hits = raycaster.intersectObjects(pickableMeshes, false).filter(h => h.object.visible);
        if (hits.length > 0 && hits[0].object.userData.hlGroup) {{
          const g = hits[0].object.userData.hlGroup;
          const found = CALLOUTS.find(c => c.group === g);
          if (found && hoveredId !== found.id) {{
            hoveredId = found.id;
            syncHighlightUI();
          }}
        }} else if (hoveredId !== null) {{
          hoveredId = null;
          syncHighlightUI();
        }}
      }});

      canvas.addEventListener('dblclick', () => {{
        lockedId = null;
        hoveredId = null;
        flyCamera([DEFAULT_CAM_POS.x, DEFAULT_CAM_POS.y, DEFAULT_CAM_POS.z], [DEFAULT_CAM_TGT.x, DEFAULT_CAM_TGT.y, DEFAULT_CAM_TGT.z], 700);
        syncHighlightUI();
      }});

      // ── Resize Handler ───────────────────────────────────────────────
      function resize() {{
        const w = stage.clientWidth;
        const h = stage.clientHeight;
        if (w < 10 || h < 10) return;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        leaderSvg.setAttribute('viewBox', `0 0 ${{w}} ${{h}}`);
      }}
      resize();
      new ResizeObserver(resize).observe(stage);

      // Initialize default Cream colorway & hide loader
      applyColorway('cream');
      syncHighlightUI();
      loaderOverlay.classList.add('done');

      // ── Main 60 FPS Animation Loop ───────────────────────────────────
      const tmpProj = new THREE.Vector3();
      const tmpCamDir = new THREE.Vector3();
      const robotCenter = new THREE.Vector3(-0.015, 0.34, 0.0);
      const hlColor = new THREE.Color();
      const zoomReadout = document.getElementById('zoom-readout');
      let lastZoomStr = '';

      function animate(now) {{
        requestAnimationFrame(animate);
        const t = now * 0.001;

        // 1. Camera fly-to smooth cubic easing
        if (camAnim) {{
          const u = Math.min(1, (now - camAnim.t0) / camAnim.dur);
          const ease = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
          camera.position.lerpVectors(camAnim.fromPos, camAnim.toPos, ease);
          controls.target.lerpVectors(camAnim.fromTgt, camAnim.toTgt, ease);
          if (u >= 1) camAnim = null;
        }}
        controls.update();

        // Update live zoom multiplier badge
        const curZoom = DEFAULT_DIST / Math.max(0.05, camera.position.distanceTo(controls.target));
        const zStr = `${{curZoom.toFixed(1)}}×`;
        if (zStr !== lastZoomStr) {{
          lastZoomStr = zStr;
          zoomReadout.textContent = zStr;
        }}

        // 2. Smooth 2-State Left Shell Cutaway <-> Full Exterior Fade
        if (Math.abs(currentLeftOpacity - targetLeftOpacity) > 0.005) {{
          currentLeftOpacity += (targetLeftOpacity - currentLeftOpacity) * 0.24;
          if (Math.abs(currentLeftOpacity - targetLeftOpacity) <= 0.005) {{
            currentLeftOpacity = targetLeftOpacity;
          }}
          const isCut = currentLeftOpacity < 0.015;
          const isFull = currentLeftOpacity >= 0.985;
          for (let i = 0; i < leftExtMeshes.length; i++) {{
            const mesh = leftExtMeshes[i];
            const m = mesh.material;
            if (isCut) {{
              mesh.visible = false;
            }} else if (isFull) {{
              mesh.visible = true;
              m.transparent = false;
              m.opacity = 1.0;
              m.depthWrite = true;
              m.roughness = mesh.userData.baseRoughness;
            }} else {{
              mesh.visible = true;
              m.transparent = true;
              m.opacity = currentLeftOpacity;
              m.depthWrite = false;
            }}
          }}
        }}

        // 3. 3D Subsystem Highlight Emissive Pulse
        const effId = getEffectiveId();
        const effGroup = effId !== null ? uiItems.get(effId).data.group : null;
        const cw = COLORWAYS[activeColorway];
        hlColor.set(cw.uiAccent);
        const pulse = 0.48 + 0.22 * Math.sin(t * 5.2);

        for (const gName in hlGroups) {{
          const isSel = gName === effGroup;
          const arr = hlGroups[gName];
          for (let i = 0; i < arr.length; i++) {{
            const mesh = arr[i];
            const m = mesh.material;
            if (isSel) {{
              m.emissive.lerp(hlColor, 0.22);
              m.emissiveIntensity += (pulse - m.emissiveIntensity) * 0.22;
            }} else {{
              m.emissive.lerp(mesh.userData.baseEmissive, 0.18);
              m.emissiveIntensity += (mesh.userData.baseEmissiveIntensity - m.emissiveIntensity) * 0.18;
            }}
          }}
        }}

        // Animate 3D beacon billboard facing camera
        if (beaconGroup.visible) {{
          beaconRing.lookAt(camera.position);
          const sc = 1.0 + 0.25 * Math.sin(t * 5.2);
          beaconRing.scale.set(sc, sc, sc);
        }}

        // 4. Project all 9 3D anchors to 2D screen pins + dynamic SVG leader lines
        const w = stage.clientWidth;
        const h = stage.clientHeight;
        tmpCamDir.subVectors(robotCenter, camera.position).normalize();
        const centerDist = camera.position.distanceTo(robotCenter);

        uiItems.forEach((item, id) => {{
          tmpProj.copy(item.anchorVec).project(camera);
          const sx = (tmpProj.x * 0.5 + 0.5) * w;
          const sy = (-tmpProj.y * 0.5 + 0.5) * h;

          // Check if pin is behind robot center relative to camera for gentle depth cue
          const pinDist = camera.position.distanceTo(item.anchorVec);
          const behind = (pinDist > centerDist + 0.085) && (id !== effId);
          item.pin.style.left = `${{sx.toFixed(1)}}px`;
          item.pin.style.top = `${{sy.toFixed(1)}}px`;
          item.pin.classList.toggle('occluded', behind);

          // Update SVG elbow polyline connecting active/visible callout card -> live 3D pin
          if (id === effId || showAllLabels) {{
            const rect = item.card.getBoundingClientRect();
            const sRect = stage.getBoundingClientRect();
            const isL = item.data.side === 'L';
            const ax = isL ? (rect.right - sRect.left) : (rect.left - sRect.left);
            const ay = (rect.top + rect.bottom) * 0.5 - sRect.top;
            const ex = isL ? ax + 22 : ax - 22;
            const pts = `${{ax.toFixed(1)}},${{ay.toFixed(1)}} ${{ex.toFixed(1)}},${{ay.toFixed(1)}} ${{sx.toFixed(1)}},${{sy.toFixed(1)}}`;
            item.halo.setAttribute('points', pts);
            item.line.setAttribute('points', pts);
          }}
        }});

        renderer.render(scene, camera);
      }}
      requestAnimationFrame(animate);

    }} catch (err) {{
      console.error('[Goose 3D Init Error]', err);
      loaderTxt.textContent = '3D WebGL 引擎初始化失败';
      loaderSub.textContent = String(err && err.message ? err.message : err);
    }}
  }}

  boot3D();
}})();
</script>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")
    raw_bytes = OUT_HTML.read_bytes()
    sha = hashlib.sha256(raw_bytes).hexdigest()

    receipt = {
        "schema": "goose005_interactive_poster_html_v1",
        "output_html": str(OUT_HTML),
        "bytes": len(raw_bytes),
        "megabytes": round(len(raw_bytes) / 1e6, 2),
        "sha256": sha,
        "elapsed_s": round(time.monotonic() - t0, 2),
        "embedded_assets": {
            "glb_gz_bytes": GLB_GZ_PATH.stat().st_size,
            "gif_beak_bytes": GIF_BEAK_PATH.stat().st_size,
            "gif_locomotion_bytes": GIF_LOCO_PATH.stat().st_size,
            "three_bundle_gz_bytes": sum(len(gzip.compress((THREE_DIR / f).read_bytes(), 9)) for f in (
                "three.module.min.js", "BufferGeometryUtils.js", "GLTFLoader.js", "OrbitControls.js", "RoomEnvironment.js"
            )),
        },
    }
    OUT_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"SAVED {OUT_HTML} ({receipt['megabytes']:.2f} MB) sha256={sha[:16]}... in {receipt['elapsed_s']}s")


if __name__ == "__main__":
    main()
