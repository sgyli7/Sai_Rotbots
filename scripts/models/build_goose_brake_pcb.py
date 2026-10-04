"""Build an independent native KiCad placement/routing candidate.

Uses pcbnew 7.0.11, not text that merely resembles a PCB. The DRC result is
reported separately from current, thermal, cold-start and manufacturing gates.
Manufacturer land drawings are numeric inputs; no runtime or training update.
"""
from pathlib import Path
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import sys
import uuid

import pcbnew as pcb
from sai_agent.goose.brake_pcb import validate_pcb_candidate, require_clean_drc

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"
OUT = ROBOT / "hardware/brake_pcb_candidate"
CONFIG = ROBOT / "configs/brake_pcb_candidate.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mm(x):
    return pcb.FromMM(float(x))


def xy(x, y):
    return pcb.VECTOR2I(mm(x), mm(y))


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,"sai-robots/goose/brake-v1/"+name))


def rectangle(owner, layer, bounds, width=.05):
    x0, y0, x1, y1 = bounds
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(points, points[1:] + points[:1]):
        line = pcb.PCB_SHAPE(owner) if isinstance(owner, pcb.BOARD) else pcb.FP_SHAPE(owner)
        line.SetShape(pcb.SHAPE_T_SEGMENT)
        if isinstance(owner, pcb.BOARD):
            line.SetStart(xy(*a)); line.SetEnd(xy(*b))
        else:
            line.SetStartEnd(xy(*a), xy(*b))
        line.SetLayer(layer); line.SetWidth(mm(width))
        owner.Add(line)


def footprint(board, ref, value, position, spec, nets, pins):
    fp = pcb.FOOTPRINT(board)
    fp.SetReference(ref); fp.SetValue(value)
    fp.SetFPID(pcb.LIB_ID("GooseBrake", spec["name"]))
    fp.SetAttributes(pcb.FP_SMD if spec.get("smd", True) else pcb.FP_THROUGH_HOLE)
    rectangle(fp, pcb.F_Fab, spec["body_bounds_mm"], .1)
    rectangle(fp, pcb.F_CrtYd, spec["courtyard_bounds_mm"])
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    for item in spec["pads"]:
        pad = pcb.PAD(fp)
        pad.SetNumber(str(item["number"]))
        pad.SetPos(xy(*item["at_mm"]))
        pad.SetSize(xy(*item["size_mm"]))
        drill = item.get("drill_mm")
        pad.SetAttribute(pcb.PAD_ATTRIB_PTH if drill else pcb.PAD_ATTRIB_SMD)
        pad.SetShape(pcb.PAD_SHAPE_RECT if not drill else pcb.PAD_SHAPE_CIRCLE)
        pad.SetLayerSet(pcb.PAD.PTHMask() if drill else pcb.PAD.SMDMask())
        if drill: pad.SetDrillSize(xy(drill, drill))
        # Separate paste windows are necessary for the large drain and EP.
        if item.get("no_paste"):
            layers = pad.GetLayerSet(); layers.RemoveLayer(pcb.F_Paste); pad.SetLayerSet(layers)
        number = str(item["number"])
        net = pins[number]["net"]
        if net is not None: pad.SetNet(nets[net])
        fp.Add(pad)
    # Paste apertures have no electrical identity.
    for item in spec.get("paste_windows", []):
        pad = pcb.PAD(fp); pad.SetNumber("")
        pad.SetPos(xy(*item["at_mm"])); pad.SetSize(xy(*item["size_mm"]))
        pad.SetAttribute(pcb.PAD_ATTRIB_SMD); pad.SetShape(pcb.PAD_SHAPE_RECT)
        layers = pcb.LSET(); layers.AddLayer(pcb.F_Paste); pad.SetLayerSet(layers)
        fp.Add(pad)
    board.Add(fp)
    fp.SetPosition(xy(*position))
    return fp


def zone(board, nets, net, layer, bounds, priority=0):
    z = pcb.ZONE(board)
    z.SetLayer(layer); z.SetNet(nets[net]); z.SetAssignedPriority(priority)
    z.SetLocalClearance(mm(.2)); z.SetMinThickness(mm(.2))
    z.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
    outline = z.Outline(); outline.NewOutline()
    x0, y0, x1, y1 = bounds
    for x, y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]: outline.Append(mm(x),mm(y))
    board.Add(z)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drc", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(CONFIG.read_text())
    validate_pcb_candidate(cfg)
    old = ROBOT / cfg["source_circuit"]
    if sha(old) != cfg["source_circuit_sha256"]: raise ValueError("changed circuit parent")
    if sha(ROBOT / cfg["source_packaging"]) != cfg["source_packaging_sha256"]:
        raise ValueError("changed packaging parent")
    OUT.mkdir(parents=True, exist_ok=True)
    board = pcb.BOARD()
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.m_BoardThickness = mm(1.6)
    settings.m_MinClearance = mm(.15)
    settings.m_CopperEdgeClearance = mm(.5)
    settings.m_TrackMinWidth = mm(.2)
    settings.m_MinThroughDrill = mm(.25)
    settings.m_NetSettings.m_DefaultNetClass.SetClearance(mm(.15))
    settings.m_SolderMaskMinWidth = mm(.1)
    settings.m_SolderMaskExpansion = mm(.03)
    nets = {}
    for part in cfg["components"]:
        for pin in part["pins"].values():
            n = pin["net"]
            if n is not None and n not in nets:
                net = pcb.NETINFO_ITEM(board, n); board.Add(net); nets[n] = net
    rectangle(board, pcb.Edge_Cuts, [0,0,80,50], .05)
    for ref, (x,y) in cfg["mounting_holes_mm"].items():
        fp = pcb.FOOTPRINT(board); fp.SetReference(ref)
        fp.SetFPID(pcb.LIB_ID("GooseBrake", "mount_hole_32"))
        fp.SetAttributes(pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        pad = pcb.PAD(fp); pad.SetAttribute(pcb.PAD_ATTRIB_NPTH)
        pad.SetShape(pcb.PAD_SHAPE_CIRCLE); pad.SetSize(xy(3.2,3.2)); pad.SetDrillSize(xy(3.2,3.2))
        pad.SetLayerSet(pcb.PAD.UnplatedHoleMask()); fp.Add(pad)
        rectangle(fp, pcb.F_CrtYd, [-3,-3,3,3]); board.Add(fp); fp.SetPosition(xy(x,y))
    footprints = {}
    for part in cfg["components"]:
        if part["kind"] == "external_resistor": continue
        footprints[part["ref"]] = footprint(board, part["ref"],part["sku"],
            cfg["placements_mm"][part["ref"]],cfg["footprints"][part["footprint"]],nets,part["pins"])
        footprints[part["ref"]].SetValue(part['value'])
        footprints[part["ref"]].SetPath(pcb.KIID_PATH('/'+uid('sheet')+'/'+uid(part['ref'])))
    library=OUT/"goose_brake.pretty"; library.mkdir(exist_ok=True)
    for fp in board.GetFootprints():
        pcb.FootprintSave(str(library),fp)
    (OUT/"fp-lib-table").write_text('(fp_lib_table (lib (name "GooseBrake") (type "KiCad") '
        '(uri "${KIPRJMOD}/goose_brake.pretty") (options "") (descr "Goose candidate lands")))\n')
    if cfg.get("routing"):
        spec = importlib.util.spec_from_file_location("goose_pcb_router", ROOT/"scripts/models/goose_pcb_router.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        route_report = module.route(board, nets, cfg)
    else:
        route_report = {"status":"PLACEMENT_ONLY", "connections_routed":0}
    zone(board,nets,"BUS",pcb.F_Cu,[.5,.5,79.5,49.5])
    zone(board,nets,"SW_RETURN",pcb.F_Cu,[30,31,79.5,49.5],1)
    zone(board,nets,"GND",pcb.B_Cu,[.5,.5,79.5,49.5])
    filename = OUT/"brake_pcb_candidate.kicad_pcb"
    pcb.SaveBoard(str(filename),board)
    # pcbnew7 Python does not expose BOARD_STACKUP editing. Read the explicit
    # proposed stack-up through the native parser; never infer 2oz from a note.
    stack='''(stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.07))
      (layer "dielectric 1" (type "core") (thickness 1.44) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.07))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG") (dielectric_constraints no)
      (edge_connector no) (castellated_pads no) (edge_plating no))'''
    filename.write_text(filename.read_text().replace('(setup\n','(setup\n    '+stack+'\n',1))
    board = pcb.LoadBoard(str(filename))
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(filename),board)
    pins = {}
    geometry_errors=[]
    for fp in board.GetFootprints():
        ref=fp.GetReference()
        if ref in footprints:
            part=next(p for p in cfg['components'] if p['ref']==ref)
            specs=cfg['footprints'][part['footprint']]['pads']
            actual=[p for p in fp.Pads() if p.GetNumber()]
            # Number, sizes AND native reloaded positions, including duplicate
            # drain pad8. A net-only comparison misses collapsed footprints.
            def sig(number,x,y,sx,sy):return (str(number),round(x,5),round(y,5),round(sx,5),round(sy,5))
            px,py=cfg['placements_mm'][ref]
            expected_geo=sorted(sig(p['number'],px+p['at_mm'][0],py+p['at_mm'][1],*p['size_mm']) for p in specs)
            actual_geo=sorted(sig(p.GetNumber(),pcb.ToMM(p.GetPosition().x),pcb.ToMM(p.GetPosition().y),
                pcb.ToMM(p.GetSize().x),pcb.ToMM(p.GetSize().y)) for p in actual)
            if expected_geo!=actual_geo:geometry_errors.append(ref)
        for pad in fp.Pads():
            if pad.GetNumber():
                pins.setdefault(fp.GetReference(),{})[pad.GetNumber()] = pad.GetNetname() or None
    expected = {p["ref"]:{n:i["net"] for n,i in p["pins"].items()}
        for p in cfg["components"] if p["kind"] != "external_resistor"}
    if pins != expected: raise ValueError("actual PCB pad identities differ from circuit")
    if geometry_errors:raise ValueError(('native pad geometry mismatch',geometry_errors))
    report = {"schema":"goose_brake_pcb_check_v1","native_version":pcb.Version(),
        "source_config_sha256":sha(CONFIG),"board_sha256":sha(filename),
        "board_parts":len(footprints),"external_resistors":8,
        "actual_pad_to_net_matches":True,"actual_reloaded_pad_geometry_matches":True,"routing":route_report,
        "drc":None,"system_release":False,"si_updated":False}
    if args.drc:
        raw = ROOT/"artifacts/Goose_V0.1/brake_pcb_review_20261004/native_drc.txt"
        raw.parent.mkdir(parents=True,exist_ok=True)
        raw.unlink(missing_ok=True)
        result = pcb.WriteDRCReport(board,str(raw),pcb.EDA_UNITS_MILLIMETRES,True)
        if not result: raise ValueError("native DRC report generation failed")
        text = raw.read_text()
        counts = require_clean_drc(text)
        report["drc"] = {"api_return":bool(result),"counts":counts,
            "report_sha256":sha(raw),"passed":not any(counts.values())}
        (ROBOT/"evidence/brake_pcb_native_drc.txt").write_text(text)
    with (OUT/"candidate_bom.csv").open("w",newline="") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(["ref","value","ordering_code_candidate","footprint","qualification"])
        for c in cfg["components"]:
            w.writerow([c["ref"],c["value"],c["sku"],c.get("footprint","off_board"),c["qualification"]])
    # Retain the parent schematic exactly. Generate this independent circuit.
    spec = importlib.util.spec_from_file_location("goose_brake_schematic", ROOT/"scripts/models/build_goose_brake_chopper.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.schematic(cfg,OUT)
    source=OUT/"absolute_brake_chopper.kicad_sch"
    data=source.read_text().replace("absolute_brake_chopper", "brake_pcb_candidate")
    data=data.replace("Goose absolute brake comparison - NOT PCB RELEASE", "Goose brake PCB candidate - NOT SYSTEM RELEASE")
    data=data.replace("Downstream BUS bias; named nets; footprints and thermal design pending", "Local decoupling and 2x825k feedback; thermal and cold-start qualification pending")
    # Instance fields and UUID links make PCB<->schematic association editable.
    by_ref={p['ref']:p for p in cfg['components']}
    lines=[];active=None
    for line in data.splitlines():
        if line.startswith('(symbol (lib_id "Goose:'):
            active=line.split('"Goose:',1)[1].split('"',1)[0]
            if by_ref[active]['kind']=='external_resistor':line=line.replace('(on_board yes)','(on_board no)')
        lines.append(line)
        if active and line.startswith('(property "Value"'):
            part=by_ref[active]
            fp_name=('GooseBrake:'+cfg['footprints'][part['footprint']]['name']) if part.get('footprint') else ''
            for index,(name,value) in enumerate([('Footprint',fp_name),('MPN',part['sku'])],2):
                lines.append(f'(property {json.dumps(name)} {json.dumps(value)} (id {index}) (at 0 0 0) '
                    '(effects (font (size 1 1)) hide))')
    data='\n'.join(lines)+'\n'
    (OUT/"brake_pcb_candidate.kicad_sch").write_text(data); source.unlink()
    (ROBOT/"evidence/brake_pcb_native_check.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ['board_parts','actual_pad_to_net_matches',
        'actual_reloaded_pad_geometry_matches','drc','system_release']}))


if __name__ == "__main__": main()
