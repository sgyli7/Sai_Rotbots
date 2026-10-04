#!/usr/bin/env python3
"""Generate a self-contained, editable comparison circuit and behavioral SPICE.

No PCB fabrication file or motor-enable command is produced by this script.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from sai_agent.goose.brake_chopper import compare, validate_circuit

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"
CONFIG = ROBOT / "configs/absolute_brake_chopper_candidate.json"
OUTPUT = ROBOT / "hardware/absolute_brake_chopper"


def schematic(config, directory):
    """Embedded symbols, deterministic IDs, native KiCad 7 format."""
    import uuid

    def uid(name):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "sai-robots/goose/brake-v1/" + name))

    def quoted(value):
        return json.dumps(value, ensure_ascii=False)

    def prop(name, value, x, y, number):
        return (f'(property {quoted(name)} {quoted(value)} (id {number}) (at {x} {y} 0) '
                '(effects (font (size 1 1))))')

    root = uid("sheet")
    libraries, instances, labels = [], [], []
    for idx, part in enumerate(config["components"]):
        ref = part["ref"]
        symbol = f"Goose:{ref}"
        pins = list(part["pins"].items())
        rows = (len(pins) + 1) // 2
        h = max(5.08, rows * 2.54)
        lib = [f'(symbol {quoted(symbol)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes)',
               prop("Reference", ref.rstrip("0123456789"), 0, h + 2.54, 0),
               prop("Value", part["value"], 0, -h - 2.54, 1),
               f'(symbol {quoted(ref + "_0_1")} (rectangle (start -8.89 {h}) (end 8.89 {-h}) '
               '(stroke (width 0.254) (type default)) (fill (type none))))',
               f'(symbol {quoted(ref + "_1_1")}']
        x, y = 41.91 + (idx % 6) * 60.96, 29.21 + (idx // 6) * 33.02
        instance = [f'(symbol (lib_id {quoted(symbol)}) (at {x:.5f} {y:.5f} 0) (unit 1) '
                    f'(in_bom yes) (on_board yes) (uuid {uid(ref)})',
                    prop("Reference", ref, x, y - h - 3.048, 0),
                    prop("Value", part["value"], x, y + h + 3.048, 1)]
        for pos, (pin, info) in enumerate(pins):
            left = pos % 2 == 0
            px = -13.97 if left else 13.97
            py = (rows - 1) * 2.54 - (pos // 2) * 5.08
            # These symbols deliberately do not claim qualified ERC semantics.
            lib.append(f'(pin passive line (at {px} {py} {0 if left else 180}) (length 5.08) '
                       f'(name {quoted(info["name"])} (effects (font (size 0.889 0.889)))) '
                       f'(number {quoted(pin)} (effects (font (size 0.889 0.889)))))')
            instance.append(f'(pin {quoted(pin)} (uuid {uid(ref + "-pin-" + pin)}))')
            ax, ay = x + px, y - py
            if info["net"] is None:
                labels.append(f'(no_connect (at {ax:.5f} {ay:.5f}) (uuid {uid(ref + "-nc-" + pin)}))')
            else:
                end_x = ax + (-5.08 if left else 5.08)
                labels.append(f'(wire (pts (xy {ax:.5f} {ay:.5f}) (xy {end_x:.5f} {ay:.5f})) '
                              '(stroke (width 0) (type default)) '
                              f'(uuid {uid(ref + "-wire-" + pin)}))')
                labels.append(f'(label {quoted(info["net"])} (at {end_x:.5f} {ay:.5f} 0) '
                              f'(effects (font (size 0.889 0.889)) (justify {"right" if left else "left"} bottom)) '
                              f'(uuid {uid(ref + "-label-" + pin)}))')
        lib.append('))')
        libraries.append("\n".join(lib))
        instance.append(f'(instances (project "absolute_brake_chopper" '
                        f'(path "/{root}" (reference {quoted(ref)}) (unit 1)))) )')
        instances.append("\n".join(instance))
    document = [f'(kicad_sch (version 20230121) (generator goose_circuit_generator) (uuid {root}) (paper "A3")',
                '(title_block (title "Goose absolute brake comparison - NOT PCB RELEASE") '
                '(date "2026-10-04") (rev "candidate_v1") '
                '(comment 1 "Downstream BUS bias; named nets; footprints and thermal design pending"))',
                '(lib_symbols', *libraries, ')', *labels, *instances,
                '(sheet_instances (path "/" (page "1")))', ')']
    (directory / "absolute_brake_chopper.kicad_sch").write_text("\n".join(document) + "\n")


def check_native_netlist(config, filename):
    tree = ET.parse(filename)
    actual = {}
    for net in tree.findall(".//nets/net"):
        nodes = {(n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node")}
        # KiCad also lists deliberate NoConn pins as unconnected-* nets.
        if not net.attrib["name"].startswith("unconnected-"):
            actual[net.attrib["name"].removeprefix("/")] = nodes
    expected = {}
    for c in config["components"]:
        for pin, info in c["pins"].items():
            if info["net"] is not None:
                expected.setdefault(info["net"], set()).add((c["ref"], pin))
    if actual != expected:
        differences = {n: {"expected": sorted(expected.get(n, set())),
                           "actual": sorted(actual.get(n, set()))}
                       for n in set(actual) | set(expected) if actual.get(n) != expected.get(n)}
        raise ValueError(f"native netlist mismatch: {differences}")
    return {"native_pin_connectivity_matches_config": True, "connected_nets": len(actual),
            "connected_pin_count": sum(map(len, actual.values())),
            "erc_or_footprints_qualified": False}


def spice(config, result, directory, scenario):
    t, p = config["threshold"], config["power_stage"]
    peak = result["shaft_power_envelope_w"]["peak"]
    count = p["dump_resistors_parallel"] - (scenario == "one_resistor_open")
    r = p["dump_resistance_each_ohm"]
    c = p["cap_count"] * p["cap_each_f"] * (1 - p["cap_tolerance_fraction"])
    esr = p["cap_esr_max_ohm_at_100khz"] / p["cap_count"]
    off = scenario == "brake_disabled"
    rows = ["Goose absolute brake behavioral network - NOT vendor semiconductor model",
        "* Upstream source opens at 0.5ms; controlled regeneration starts at 0.75ms.",
        "* Bias/reference are pre-established ideal sources, not a cold-start model.",
        "* ESR at 100kHz, no wire inductance, equal current sharing, no thermal solver.",
        "* Constant-current gate capacitance approximation Qg/4.5; Ron-only FET switch.",
        "Vbattery battery 0 25.2", "Vsource source_enable 0 PWL(0 5 499u 5 500u 0 4m 0)",
        "Ssource battery bus source_enable 0 SOURCE", ".model SOURCE SW(Ron=0.001 Roff=1e12 Vt=2.5 Vh=0.1)",
        f"Bregen 0 bus I=({peak:.15g}*(time>0.00075))/max(v(bus),1)",
        f"Rbulk bus storage {esr:.15g}", f"Cbulk storage 0 {c:.15g} IC=25.2",
        "Vbias bias 0 5", "Vreference reference 0 2.5",
        f"Rtop bus sense {t['top_ohm']}", f"Rbottom sense 0 {t['bottom_ohm']}",
        f"Rfeedback request sense {t['feedback_ohm']}", f"Csense sense 0 {t['sense_cap_f']}",
        "Bcomparator raw 0 V=" + ("0" if off else "2.5*(1+tanh((v(sense)-v(reference))/0.0001))"),
        "* RC lag is a declared behavioral approximation, not a datasheet maximum guarantee.",
        "Rcmp raw request 100", "Ccmp request 0 550p",
        "Bdriver driver_raw 0 V=5*(v(request)>2.4)", "Rdriver driver_raw drive 11",
        f".model BRAKE SW(Ron={p['mosfet_rds_at_4_5v_max_ohm']*p['mosfet_hot_resistance_multiplier_assumed']} Roff=1e12 Vt=4.5 Vh=0.01)"]
    for n in range(1, p["mosfet_parallel_count"] + 1):
        rows += [f"RG{n} drive gate{n} 2.2", f"RP{n} gate{n} 0 100k",
                 f"CG{n} gate{n} 0 {p['mosfet_gate_charge_at_4_5v_max_c']/4.5:.15g}",
                 f"Sbrake{n} switched 0 gate{n} 0 BRAKE"]
    for n in range(1, count + 1):
        rows.append(f"RD{n} bus switched {r}")
    rows += [".ic V(bus)=25.2 V(storage)=25.2 V(sense)=2.421661154",
             ".options reltol=0.001 abstol=1e-9 vntol=1e-6",
             ".control", "set wr_singlescale", "set wr_vecnames",
             "save all @bregen[i] @rd1[i]",
             "tran 50n 4m 0 50n uic",
             f"wrdata {directory.resolve()}/{scenario}.tsv v(bus) v(storage) v(request) v(gate1) v(sense) @bregen[i] @rd1[i]",
             "quit", ".endc", ".end"]
    (directory / f"{scenario}.cir").write_text("\n".join(rows) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-netlist", type=Path)
    parser.add_argument("--spice-output", type=Path)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    validate_circuit(config)
    current_parameters = json.loads((ROOT / config["source_hardware_parameters"]).read_text())
    current_ledger = {item["name"]: item["mass_kg"] for item in current_parameters["items"]}
    for name, mass in config["mechanical_candidate"]["existing_reserved_mass_items_kg"].items():
        if current_ledger.get(name) != mass:
            raise ValueError("candidate protection reserve differs from current assembly ledger")
    result = compare(config, json.loads((ROBOT / "configs/mechanical_physics_contract.json").read_text()))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    schematic(config, OUTPUT)
    with (OUTPUT / "candidate_bom.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["reference", "value", "ordering_code_or_pending", "vendor_source", "footprint_released"])
        for c in config["components"]:
            writer.writerow([c["ref"], c["value"], c["sku"], config["sources"].get(c["source"], {}).get("url", ""), False])
    if args.native_netlist:
        result["kicad_native_parse"] = check_native_netlist(config, args.native_netlist)
    if args.spice_output:
        args.spice_output.mkdir(parents=True, exist_ok=True)
        for scenario in ("nominal", "one_resistor_open", "brake_disabled"):
            spice(config, result, args.spice_output, scenario)
    paths = [CONFIG, ROOT / "src/sai_agent/goose/brake_chopper.py", Path(__file__),
             ROBOT / "configs/mechanical_physics_contract.json",
             ROBOT / "evidence/manual_wing_service_parameters.json", *OUTPUT.iterdir()]
    result["source_hashes"] = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                               for f in sorted(paths) if f.is_file()}
    (ROBOT / "evidence/absolute_brake_chopper_comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"components": len(config["components"]), "conditional_response": result["response"],
                      "release": False, "kicad": result.get("kicad_native_parse")}))


if __name__ == "__main__":
    main()
