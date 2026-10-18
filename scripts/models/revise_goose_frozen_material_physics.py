"""Create a separately versioned physics package from approved material MCI.

The producer packet is selected by the project manager after source-bound
screening. This tool never infers strength from density or collision volume.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
JAW_OWNERS = {
    **dict.fromkeys(("beak_native_input_flange", "beak_input_steel_sleeve",
                     "beak_input_washer", "beak_input_button_screw"), "beak_input_rotor"),
    **dict.fromkeys(("beak_native_coupler", "beak_input_bush_candidate",
                     "beak_output_bush_candidate"), "beak_coupler_link"),
}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def combined(rows):
    mass = sum(r["mass_kg"] for r in rows)
    centre = sum(r["mass_kg"] * np.array(r["centre_zero_mm"]) / 1000
                 for r in rows) / mass
    tensor = np.zeros((3, 3))
    for r in rows:
        d = np.array(r["centre_zero_mm"]) / 1000 - centre
        tensor += np.array(r["inertia_at_com_zero_kg_m2"]) + r["mass_kg"] * (
            d @ d * np.eye(3) - np.outer(d, d))
    tensor = (tensor + tensor.T) / 2
    eig = np.linalg.eigvalsh(tensor)
    if eig[0] <= 0 or eig[2] > eig[0] + eig[1] + 1e-10:
        raise ValueError("Nonphysical complete inertia")
    return mass, centre, tensor


def main(a):
    baseline, output = a.baseline.resolve(), a.output.resolve()
    if output.exists():
        raise FileExistsError("Revision output must be a new immutable directory")
    contract = read(baseline / "physical_contract.json")
    ledger = read(baseline / "mass_ledger.json")
    drive = read(baseline / "actuator_contract.json")
    packet = read(a.approved_material_packet)
    parts = packet["parts"]
    items = copy.deepcopy(ledger["items"])
    index = {r["name"]: i for i, r in enumerate(items)}
    if len(index) != len(items):
        raise ValueError("Duplicate baseline mass names")
    applied, touched = [], set()
    for p in parts:
        name = p["name"]
        if name in touched:
            raise ValueError("Repeated replacement: " + name)
        touched.add(name)
        old = copy.deepcopy(items[index[name]])
        if old["body"] != p["body"]:
            raise ValueError("Material revision may not change owner: " + name)
        centre = p.get("center_of_mass_world_m")
        tensor = p.get("inertia_at_com_world_kg_m2")
        if centre is None or tensor is None:
            raise ValueError("Packet requires complete source-native SI MCI")
        new = copy.deepcopy(old)
        new.update(mass_kg=p["mass_kg"],
                   centre_zero_mm=(np.array(centre) * 1000).tolist(),
                   inertia_at_com_zero_kg_m2=tensor,
                   material=p.get("material"), density_kg_m3=p.get("density_kg_m3"),
                   inertia_basis="Manager-selected, source-bound material candidate complete native MCI; not a physical measurement",
                   source_material_packet_part=name,
                   measured_mass_or_inertia=False)
        if "mass_interval_kg" in new:
            new["historical_parent_mass_interval_kg"] = new.pop("mass_interval_kg")
        new["fixed_design_mass_for_this_physics_revision"] = True
        new["selected_native_source"] = p.get("native", dict(
            path=p.get("native_brep_path"), sha256=p.get("native_brep_sha256")))
        # Independent positive/triangle checks apply also to each new part.
        combined([new])
        items[index[name]] = new
        applied.append(dict(operation="same_named_source_material_replacement",
                            name=name, old=old, new=new,
                            delta_mass_kg=new["mass_kg"] - old["mass_kg"]))
    regrouped = copy.deepcopy(items)
    for r in regrouped:
        leaf = r["name"].rsplit("/", 1)[-1]
        r["body"] = JAW_OWNERS.get(leaf, r["body"])
    if {r["body"] for r in regrouped} != {b["name"] for b in contract["bodies"]}:
        raise ValueError("Rigid owner coverage changed")
    body_changes = []
    for b in contract["bodies"]:
        old = copy.deepcopy(b)
        rows = [r for r in regrouped if r["body"] == b["name"]]
        mass, centre, tensor = combined(rows)
        b.update(mass_kg=mass, centre_world_zero_m=centre.tolist(),
                 com_local_m=(centre - np.array(b["origin_world_zero_m"])).tolist(),
                 inertia_at_com_world_zero_kg_m2=tensor.tolist(),
                 inertia_at_com_body_kg_m2=tensor.tolist(), item_count=len(rows),
                 source_mass_items=[r["name"] for r in rows])
        body_changes.append(dict(name=b["name"], old=old, new=copy.deepcopy(b)))
    total = sum(r["mass_kg"] for r in items)
    if abs(total - sum(b["mass_kg"] for b in contract["bodies"])) > 1e-10:
        raise ValueError("Body total and ledger differ")
    baseline_mass = ledger["nominal_mass_kg"]
    reference = dict(repository_path=str(a.approved_material_packet.resolve().relative_to(ROOT)),
                     sha256=sha(a.approved_material_packet), required_at_runtime=False)
    contract.update(release_id=output.name, contract_revision=3,
                    nominal_robot_mass_kg=total,
                    previous_unpublished_baseline=dict(release_id=baseline.name,
                                                       physical_contract_sha256=sha(baseline / "physical_contract.json"),
                                                       mass_kg=baseline_mass),
                    selected_material_revision=reference,
                    actuator_capabilities_changed=False)
    contract["sources"].append(reference)
    ledger.update(items=items, nominal_mass_kg=total,
                  selected_material_revision=reference, material_revision_operations=applied,
                  previous_unpublished_baseline_mass_kg=baseline_mass,
                  material_revision_net_delta_kg=total - baseline_mass)
    drive["release_id"] = output.name
    drive["canonical_adapter_source"] = dict(
        repository_path="src/sai_agent/goose/frozen_physics_runtime.py",
        sha256=sha(ROOT / "src/sai_agent/goose/frozen_physics_runtime.py"),
        required_at_runtime=False)
    drive["reference_adapter"] = "runtime_adapter.py"
    output.mkdir(parents=True)
    for path in baseline.iterdir():
        if path.is_file() and path.name not in {
            "manifest.json", "robot.xml", "collision_manifest.json", "runtime_interface.json",
            "mass_ledger.json", "physical_contract.json", "actuator_contract.json", "freeze_summary.json",
        }:
            shutil.copyfile(path, output / path.name)
    save(output / "physical_contract.json", contract)
    save(output / "mass_ledger.json", ledger)
    save(output / "actuator_contract.json", drive)
    shutil.copyfile(a.approved_material_packet, output / "material_mass_patch.json")
    save(output / "material_change_receipt.json", dict(
        schema="goose_source_bound_material_revision_v1", release_id=output.name,
        manager_selected_packet=reference, previous_baseline_was_unpublished=True,
        baseline_mass_kg=baseline_mass, final_mass_kg=total,
        delta_mass_kg=total - baseline_mass, operations=applied,
        body_changes=body_changes, collision_mass_inference_used=False,
        actuator_capabilities_changed=False))
    snapshot = read(output / "source_snapshot.json")
    snapshot.update(release_id=output.name, material_revision=reference,
                    previous_unpublished_baseline=contract["previous_unpublished_baseline"])
    embedded = []
    for ref in contract["sources"]:
        name = Path(ref["repository_path"]).name
        if name not in {"conditional_mass_ledger.json", "whole05_full_SI_contract.json"}:
            continue
        original = ROOT / ref["repository_path"]
        if sha(original) != ref["sha256"]:
            raise ValueError("Historical source changed before embedding: " + name)
        target = output / "source_inputs" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(original, target)
        embedded.append(dict(repository_path=ref["repository_path"],
                             package_path=str(target.relative_to(output)),
                             sha256=ref["sha256"], required_at_runtime=False))
    embedded.extend([
        dict(repository_path=next(r["repository_path"] for r in contract["sources"]
                                  if r["repository_path"].endswith("E_simulation_mass_contract.json")),
             package_path="engineering_mass_patch.json", sha256=sha(output / "engineering_mass_patch.json"),
             required_at_runtime=False),
        dict(repository_path=reference["repository_path"], package_path="material_mass_patch.json",
             sha256=reference["sha256"], required_at_runtime=False),
    ])
    snapshot["embedded_source_contracts"] = embedded
    checkpoint = ROOT / "robots/goose_v0_2/cad/source/engineering_checkpoint_20261018/checkpoint_manifest.json"
    if checkpoint.exists():
        snapshot["portable_whole05_engineering_checkpoint"] = dict(
            repository_path=str(checkpoint.relative_to(ROOT)), sha256=sha(checkpoint),
            required_at_runtime=False,
            scope="1824-part native hardware checkpoint before final design mass/material changes; apply selected material patch separately, not a manufacturing release")
    save(output / "source_snapshot.json", snapshot)
    summary = dict(total_mass_kg=total, baseline_unpublished_mass_kg=baseline_mass,
                   material_delta_kg=total - baseline_mass, body_count=len(contract["bodies"]),
                   public_axes=18, internal_coordinates=4,
                   E_delta_kg=contract["engineering_allocation_delta_kg"],
                   native_internal_helper_joint_damping_nm_s_rad={
                       j["name"]: j.get("damping_nm_s_rad", .01)
                       for j in contract["passive_linkage_joints"]},
                   physical_contract_sha256=sha(output / "physical_contract.json"),
                   actuator_contract_sha256=sha(output / "actuator_contract.json"),
                   mass_ledger_sha256=sha(output / "mass_ledger.json"))
    save(output / "freeze_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--approved-material-packet", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
