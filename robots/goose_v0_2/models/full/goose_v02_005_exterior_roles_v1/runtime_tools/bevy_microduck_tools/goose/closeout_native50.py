"""Named Goose V0.2 closeout candidate on the existing native-discrete stack.

The candidate has its own source identity; it is never a replacement for an
older frozen candidate and this module does not grant training qualification.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from .artifacts import DT, JOINT_ORDER, sha256
from .upstream_discrete_mjlab import VERSIONS, require_upstream_stack

CANDIDATE = "goose_v02_closeout_native50_20261108"
PRODUCTION_CANDIDATE = 'goose_v02_native50_source007_adopted_20261110_v1'
PRODUCTION_RUNTIME_REQUIREMENTS={'gpu_use_cuda_graph':False,'num_envs':2,'training_horizon_ticks':32,
    'collision_module_sha256':'539cd69baaf104e604e6e0c06de5cebbc0a4a7b798fc3bf4c800ee94b151b534'}
CONTACT_LITE_CANDIDATE = 'goose_v02_005_exterior_roles_v1'
LITE_RUNTIME_REQUIREMENTS = dict(PRODUCTION_RUNTIME_REQUIREMENTS, allowed_num_envs=[2, 32])
TRAINING_CANDIDATES = (PRODUCTION_CANDIDATE, CONTACT_LITE_CANDIDATE)
CANDIDATES = (CANDIDATE, *TRAINING_CANDIDATES)
SCHEMA = "goose_v02_closeout_native50_v1"
REVISION = "goose_v02_closeout_native50_mjlab_v1"
BASELINE_MODEL_SHA256 = "c2f0f55e3048691fd6a1618c6990fba596880f6711f740eca17d6f81765878cb"
BASELINE_CONTRACT_SHA256 = "8b17aa7d7316c3f36d6949fe79a6392cc6c216f0ea7aa4b82c100c3337116794"
MOTOR_ORDER = (*JOINT_ORDER[:5], "beak_input_rotor", *JOINT_ORDER[6:])
ACTION_SEMANTICS = "clip(q_neutral + max(abs(lo-q_neutral),abs(hi-q_neutral))*clip(action,-1,1),lo,hi); index5 is physical beak_input_rotor; native 50Hz drive"
DIAGNOSTIC_PROFILE = {'name':'source_faithful_diagnostic_8192_v3',
    'contact_leaf_limit':8192, 'support_vertices_per_leaf_limit':128,
    'total_support_vertices_limit':250000, 'training_ready':False,
    'scope':'geometry_and_actual20ms_diagnostics_only',
    'protected_manifest_sha256':'72d83f7ad3e8c187206c3064fc14366d70d2e51ae7c5740bb860392953e34996',
    'protected_exact_support_vertices_limit':216}
PRODUCTION_PROFILE = dict(DIAGNOSTIC_PROFILE,
    name='source_faithful_production_8192_v1',training_ready=True,
    scope='native50_simulation_training_entry')


def contact_leaf_limit(contract):
    if contract.get('candidate') == CONTACT_LITE_CANDIDATE:
        return 64
    if contract.get('candidate') == PRODUCTION_CANDIDATE:
        if contract.get('closeout_native50', {}).get('production_profile') != PRODUCTION_PROFILE:
            raise ValueError('Unsupported adopted production budget profile')
        return PRODUCTION_PROFILE['contact_leaf_limit']
    profile = contract.get('closeout_native50', {}).get('diagnostic_profile')
    if profile is None:
        return 128
    if profile != DIAGNOSTIC_PROFILE:
        raise ValueError('Unsupported closeout diagnostic budget profile')
    return DIAGNOSTIC_PROFILE['contact_leaf_limit']


# Exact protected_contacts_001/contact_manifest_002 identities. These retained
# six assets may not be simplified merely to meet the new-fragment budget.
PROTECTED_SUPPORT_IDENTITIES = {
    'lower_grip_cassette_pad__grip_plane': ('beak_hinge', 'bdd4b067ea4964f594d5ec2c5a88d486a70daa8d324a35ca8028231218b65cac', '62f8c9d2349773c9894a3d22ae80192454520f5ec582b0a4980a193096819f82'),
    'upper_grip_cassette_pad__grip_plane': ('head_roll', 'ee79b1ab502570b0d1faffe5f93409e2e481416a2bc57376ed8e0f4acdc06447', 'c86843ec1504f58ff57928038ea1848cc429bed11d8130034a9a3b0af5c01e67'),
    'left_flat_rounded_sole__support': ('left_ankle_roll', '5193b90a10cc68517b56534c7863392ffda5b04c8b2abc1cdbfcf49ff6831777', '9d1b642074ecb79269ee6e280738ae0a8a2512af893454375d6cc92cc19fe3a2'),
    'left_flat_rounded_sole__upper_support': ('left_ankle_roll', 'ba9ea419bd81e700bd71f7f6b2a8961b634f5da2778c0b4701501e660e166722', '9d1b642074ecb79269ee6e280738ae0a8a2512af893454375d6cc92cc19fe3a2'),
    'right_flat_rounded_sole__support': ('right_ankle_roll', '8b866728d1e2dc31aac7345c9de7de2e9eb84ca38b8c4d6de3b346b6cc469a1f', '68c94384f3a890c6d763f25950c785cd2f2d482d544429490be7832540ab792a'),
    'right_flat_rounded_sole__upper_support': ('right_ankle_roll', 'f1513b764f10020b42524a053cea02d27a2a002d9be62b4004701fd84c1c6630', '68c94384f3a890c6d763f25950c785cd2f2d482d544429490be7832540ab792a'),
}


def diagnostic_support_limit(leaf, contact):
    expected = PROTECTED_SUPPORT_IDENTITIES.get(leaf['name'])
    source_ids = leaf.get('native_source_sha256s') or [leaf.get('native_source_sha256')]
    if (expected is not None and leaf.get('input_role') == 'protected'
            and contact.get('input_refs', {}).get('protected', {}).get('sha256') == DIAGNOSTIC_PROFILE['protected_manifest_sha256']
            and (leaf.get('owner'), leaf.get('mesh_source', {}).get('sha256'), *source_ids) == expected):
        return DIAGNOSTIC_PROFILE['protected_exact_support_vertices_limit']
    return DIAGNOSTIC_PROFILE['support_vertices_per_leaf_limit']


def validate_compiled_motor_limits(model, contract):
    """Read physical motor-side limits, including the effort-controlled rotor."""
    for index, joint in enumerate(contract['joints']):
        peak = joint['torque_peak_limit_nm']
        if not np.array_equal(model.actuator_gear[index], np.array([1.,0.,0.,0.,0.,0.])):
            raise ValueError('Closeout physical motor gear differs: '+joint['name'])
        if index == 5:
            if (not model.actuator_ctrllimited[index]
                    or not np.allclose(model.actuator_ctrlrange[index],[-peak,peak],atol=1e-12,rtol=0)):
                raise ValueError('Closeout physical rotor effort limit differs from actual020')
        elif (not model.actuator_forcelimited[index]
                or not np.allclose(model.actuator_forcerange[index],[-peak,peak],atol=1e-12,rtol=0)):
            raise ValueError('Closeout physical motor torque limit differs: '+joint['name'])


def contact_shape_supported(kind):
    # MuJoCo3.15 enum tuple-membership is asymmetric for NumPy scalar inputs.
    # Compare plain integers from both APIs, as the existing geometry exporter does.
    return int(kind) in (int(mujoco.mjtGeom.mjGEOM_MESH),int(mujoco.mjtGeom.mjGEOM_BOX))


def cold_birth_contact_check(model, data, contact_manifest):
    """Read native contacts before the first Tick; never alter pair filtering.

    Existing physical connection exclusions remain in the model. Only the two
    hash-bound closed-grip pad surfaces may meet within float32 mesh roundoff.
    Other penetrating body pairs are rejected for source-level adjudication.
    """
    leaves = {leaf['name']:leaf for leaf in contact_manifest['leaves']}
    closed_grip = {'lower_grip_cassette_pad__grip_plane','upper_grip_cassette_pad__grip_plane'}
    blocked, boundaries = [], []
    for index in range(data.ncon):
        hit = data.contact[index]
        a,b = int(hit.geom1),int(hit.geom2)
        ba,bb = int(model.geom_bodyid[a]),int(model.geom_bodyid[b])
        if not ba or not bb or float(hit.dist) >= 0:
            continue
        names = (model.geom(a).name,model.geom(b).name)
        row = {'native_contact_index':index,'geoms':list(names),'owners':[model.body(ba).name,model.body(bb).name],
               'penetration_m':-float(hit.dist),'position_runtime_world_m':hit.pos.tolist(),
               'normal_runtime_world':hit.frame[:3].tolist()}
        # Numerical allowance applies only to the unchanged exact pad assets,
        # and is explicitly reported. It is not a general clearance tolerance.
        roundoff = float(np.finfo(np.float32).eps * max(1.,np.abs(data.geom_xpos[[a,b]]).max()))
        if (set(names) == closed_grip
                and all(diagnostic_support_limit(leaves[name],contact_manifest) == 216 for name in names)
                and row['penetration_m'] <= roundoff):
            row['closed_grip_mesh_roundoff_m'] = roundoff
            boundaries.append(row)
        else:
            blocked.append(row)
    return {'passed':not blocked,'blocked_self_contacts':blocked,
            'retained_closed_grip_boundaries':boundaries,'pair_masks_changed':False}


def _source(ref, label, root=None):
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
        raise ValueError(f"Invalid {label} source reference")
    path = Path(ref["path"])
    if not path.is_absolute():
        if root is None or '..' in path.parts:
            raise ValueError(f"Invalid package-local {label} source reference")
        path = Path(root) / path
    path = path.resolve(strict=True)
    if root is not None and not Path(ref['path']).is_absolute() and not path.is_relative_to(root):
        raise ValueError(f"Escaping package-local {label} source reference")
    if not path.is_file() or sha256(path) != ref["sha256"]:
        raise ValueError(f"{label} source identity changed")
    return path


def _asset(root, relative, digest):
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or sha256(path) != digest:
        raise ValueError(f"Candidate asset identity changed: {relative}")


def validate_source_contract(model_path: Path, contract_path: Path):
    """Validate the named source and immutable control semantics; no integration."""
    model_path = Path(model_path).resolve(strict=True)
    contract_path = Path(contract_path).resolve(strict=True)
    contract = json.loads(contract_path.read_text())
    identity = contract.get("closeout_native50", {})
    identity.pop('_resolved_gravity_source_root', None)
    production = contract.get('candidate') == PRODUCTION_CANDIDATE
    lite = contract.get('candidate') == CONTACT_LITE_CANDIDATE
    if (contract.get("schema") != SCHEMA or contract.get("candidate") not in CANDIDATES
            or identity.get("revision") != REVISION or identity.get("versions") != VERSIONS
            or contract.get("training_release") is not False
            or contract.get("model_sha256") != sha256(model_path)
            or contract.get("integrator") != "discrete"
            or contract.get("joint_order") != list(MOTOR_ORDER)
            or contract.get("action_semantics") != ACTION_SEMANTICS
            or contract.get("legacy_policy_compatible") is not False
            or contract.get("action_size") != 18
            or contract.get("observation_sizes", {}).get("locomotion") != 65
            or contract.get("observation_sizes", {}).get("recovery") != 65
            or any(contract.get(k) != DT for k in ("physics_dt_s", "torque_dt_s", "policy_dt_s"))
            or any(contract.get(k) != 1 for k in ("physics_steps_per_tick", "torque_updates_per_tick", "policy_calls_per_tick"))):
        raise ValueError("Closeout native50 schema, timing or interface mismatch")
    refs = identity.get("source_refs", {})
    required = {"assembly", "contact", "motion", "mci", "fk_receipt", "fk_xml", "hardware_contract", "beak_mapping_module", "beak_mapping_evidence", "baseline_model", "baseline_contract"}
    if set(refs) != required:
        raise ValueError("Closeout requires all eleven hash-bound source references")
    paths = {name: _source(ref, name, contract_path.parent) for name, ref in refs.items()}
    baseline = json.loads(paths["baseline_contract"].read_text())
    if (baseline.get("candidate") != "goose_task_proxy_11_discrete_mjlab160_v1"
            or refs["baseline_model"]["sha256"] != BASELINE_MODEL_SHA256
            or refs["baseline_contract"]["sha256"] != BASELINE_CONTRACT_SHA256
            or baseline.get("model_sha256") != refs["baseline_model"]["sha256"]):
        raise ValueError("Frozen native50 training baseline identity mismatch")
    for key in ("action_size", "observation_sizes", "phase_frequency_hz", "controller_revision", "source_checkpoint"):
        if contract.get(key) != baseline.get(key):
            raise ValueError(f"Closeout changes frozen policy semantics: {key}")
    if 'portable_gravity_root' in identity:
        relative = Path(identity['portable_gravity_root'])
        root = (contract_path.parent / relative).resolve(strict=True)
        if relative.is_absolute() or '..' in relative.parts or not root.is_relative_to(contract_path.parent):
            raise ValueError('Invalid portable gravity source root')
        checkpoint = contract['source_checkpoint']
        module = 'src/sai_agent/goose/stage_one_gravity.py'
        if sha256(root/module) != checkpoint['source_module_sha256'][module]:
            raise ValueError('Portable nominal gravity source identity mismatch')
        identity['_resolved_gravity_source_root'] = str(root)
    if contract.get("rigid_native", {}).get("signed_braking") != baseline.get("rigid_native", {}).get("signed_braking"):
        raise ValueError("Closeout changes the frozen braking-control semantics")
    hardware = json.loads(paths["hardware_contract"].read_text())
    motion = json.loads(paths["motion"].read_text())
    hardware_joints = {item["name"]: item for item in hardware["joints"]}
    motion_joints = {item["name"]: item for item in motion["active_joints"]}
    joints, old_joints = contract.get("joints", []), baseline.get("joints", [])
    control_fields = ("kp_nm_rad", "kd_nm_s_rad", "torque_peak_limit_nm",
                      "continuous_design_limit_nm", "speed_limit_rad_s", "actuator")
    if (len(joints) != 18 or [item["name"] for item in joints] != list(MOTOR_ORDER)
            or set(hardware_joints) != set(MOTOR_ORDER) or set(motion_joints) != set(MOTOR_ORDER)):
        raise ValueError("Closeout physical motor inventory mismatch")
    for index, item in enumerate(joints):
        name = item["name"]
        if any(item.get(key) != hardware_joints[name].get(key) for key in control_fields):
            raise ValueError(f"Closeout motor parameters differ from 020 source: {name}")
        if index not in (5, 6, 12) and any(item.get(key) != old_joints[index].get(key) for key in control_fields):
            raise ValueError(f"Closeout unexpectedly changed a retained drive: {name}")
        limits = np.asarray(motion_joints[name]["range_rad"], float)
        neutral = hardware_joints[name]["q_neutral_rad"]
        scale = max(abs(limits[0]-neutral), abs(limits[1]-neutral))
        if (not np.allclose(item["range_rad"], limits, atol=1e-12, rtol=0)
                or item["q_neutral_rad"] != neutral or not np.isclose(item["action_scale_rad"],scale,atol=1e-12,rtol=0)):
            raise ValueError(f"Closeout physical action normalization mismatch: {name}")
    evidence = json.loads(paths["beak_mapping_evidence"].read_text())
    if (evidence.get("status") != "PASS" or evidence.get("implementation_sha256") != refs["beak_mapping_module"]["sha256"]
            or evidence.get("source_sha256", {}).get("robot.xml") != refs["fk_xml"]["sha256"]
            or evidence.get("source_sha256", {}).get("physical_contract.json") != refs["hardware_contract"]["sha256"]):
        raise ValueError("Closeout beak linkage evidence does not bind the current 020 source")
    qualification = contract.get("qualification", {})
    if (contract.get("source_runtime") != "bevy_microduck_tools.goose.closeout_native50.make_source_runtime"
            or any(contract.get(k) is not False for k in ("manufacturing_pass", "hardware_freeze", "final_appearance_pass"))
            or qualification.get('engineering_entry') is not (production or lite and contract.get('training_ready') is True)
            or any(qualification.get(k) is not False for k in ("learned_locomotion", "learned_recovery", "pickup", "dragging", "godot_jolt", "unity"))):
        raise ValueError("Closeout runtime or qualification identity invalid")
    if lite:
        from .contact_lite_validation import validate_lite_contract
        validate_lite_contract(contract, contract_path.parent)
    if production:
        if identity.get('runtime_requirements') != PRODUCTION_RUNTIME_REQUIREMENTS:
            raise ValueError('Production runtime requires uncaptured GPU/twoworld32tick profile')
        from .closeout_bundle import validate_adoption_document
        if contract.get('training_ready') is not True or identity.get('diagnostic_profile') is not None:
            raise ValueError('Adopted production must have its independent ready identity')
        adoption_files = identity.get('adoption_files', {})
        def adoption_source(ref):
            relative = adoption_files.get(ref.get('sha256'))
            if relative is None:
                raise ValueError('Missing archived adoption evidence')
            return _source({'path':relative,'sha256':ref['sha256']},'adoption evidence',contract_path.parent)
        approval_path = adoption_source(identity['production_adoption'])
        parent_path = adoption_source(identity['adopted_from_contract'])
        validate_adoption_document(json.loads(approval_path.read_text()),adoption_source,
            sha256(model_path),sha256(parent_path),{name:ref['sha256'] for name,ref in refs.items()})
    for relative, digest in contract.get("asset_sha256", {}).items():
        _asset(model_path.parent, relative, digest)
    if not contract.get("asset_sha256"):
        raise ValueError("Closeout geometry asset map is empty")
    xml = ET.parse(model_path).getroot()
    pair_policy = contract.get("rigid_native", {}).get("contact_pair_policy", {})
    expected_pair = {"beak_hinge", "beak_coupler_link"}
    excludes = xml.findall("./contact/exclude")
    flag = xml.find("./option/flag")
    if (pair_policy.get("explicit_excludes") != [["beak_hinge", "beak_coupler_link"]]
            or pair_policy.get("parent_child_filter") != "enabled_mujoco_default"
            or pair_policy.get("legacy_11_leaf_excludes_inherited") is not False
            or len(excludes) != 1 or {excludes[0].get("body1"), excludes[0].get("body2")} != expected_pair
            or (flag is not None and flag.get("filterparent", "enable") != "enable")):
        raise ValueError("Closeout collision exclusion policy mismatch")
    mesh_files = {item.get("file") for item in xml.findall("./asset/mesh") if item.get("file")}
    if not mesh_files.issubset(contract["asset_sha256"]):
        raise ValueError("Every referenced mesh must be hash-bound")
    contact = json.loads(paths["contact"].read_text())
    expected_contact_profile = DIAGNOSTIC_PROFILE if production else identity.get('diagnostic_profile')
    if contact.get('diagnostic_profile') != expected_contact_profile:
        raise ValueError('Contact and runtime diagnostic budget profiles differ')
    if contact.get("contact_pair_policy") != pair_policy:
        raise ValueError("Contact manifest and runtime pair policy differ")
    if contact.get("complete") is not True:
        raise ValueError("Partial or rejected geometry binding is not a candidate")
    for field, key in (("source_assembly", "assembly"), ("source_motion", "motion"),
                       ("source_MCI", "mci"), ("source_FK", "fk_receipt")):
        if contact.get(field, {}).get("sha256") != refs[key]["sha256"]:
            raise ValueError(f"Contact source binding mismatch: {field}")
    leaves = contact.get("leaves", [])
    if (not 1 <= contact.get("leaf_count", 0) <= contact_leaf_limit(contract)
            or len(leaves) != contact["leaf_count"]
            or len({leaf["name"] for leaf in leaves}) != len(leaves)):
        raise ValueError("Closeout robot-contact inventory outside the Owner limit")
    assembly = json.loads(paths["assembly"].read_text())
    assembly_rows = {row['name']: row for row in assembly['parts']}
    if len(assembly_rows) != len(assembly['parts']):
        raise ValueError('Duplicate assembly occurrence')
    hashes = {row['source'].get('source_native_sha256') or row['source'].get('sha256') for row in assembly_rows.values()}
    for leaf in leaves:
        source_ids = leaf.get("native_source_sha256s") or ([leaf["native_source_sha256"]] if leaf.get("native_source_sha256") else [])
        if not source_ids or len(source_ids) != len(set(source_ids)) or any(value not in hashes for value in source_ids):
            raise ValueError(f"Contact leaf missing assembly-native binding: {leaf['name']}")
        if not leaf.get('source_occurrence_bindings'):
            raise ValueError('Missing explicit contact source occurrence')
        for binding in leaf['source_occurrence_bindings']:
            current = assembly_rows.get(binding['name'])
            native = (current or {}).get('source', {})
            if (current is None or current['owner'] != binding['owner']
                    or (native.get('source_native_sha256') or native.get('sha256')) != binding['native_source_sha256']
                    or not np.allclose(current['source_to_world_mm'], binding['source_to_world_mm'], atol=1e-10, rtol=0)):
                raise ValueError(f"Contact occurrence mismatch: {binding['name']}")
        if leaf.get("mesh_file") and leaf["mesh_file"] not in contract["asset_sha256"]:
            raise ValueError(f"Contact leaf missing mesh hash: {leaf['name']}")
    # Consumers receive verified resolved paths; the on-disk portable contract
    # retains relative references and its original hash-bound source bytes.
    for name, path in paths.items():
        refs[name]['path'] = str(path)
    return contract, paths, contact


def make_source_runtime(model_path: Path, contract_path: Path):
    """Load the new plant on the frozen drive without reusing old candidate ID."""
    require_upstream_stack()
    contract, paths, contact = validate_source_contract(model_path, contract_path)
    model = mujoco.MjModel.from_xml_path(str(model_path))
    baseline = mujoco.MjModel.from_xml_path(str(paths["baseline_model"]))
    if model.nbody != 22 or model.nu != 18 or model.nflex != 0 or model.neq != 1:
        raise ValueError("Closeout native body/actuator/flex/beak count mismatch")
    if model.opt.timestep != DT or model.opt.integrator != mujoco.mjtIntegrator.mjINT_DISCRETE:
        raise ValueError("Closeout must retain 50 Hz native-discrete physics")
    for key in dir(baseline.opt):
        if key.startswith("_") or callable(value := getattr(baseline.opt, key)):
            continue
        if not np.array_equal(value, getattr(model.opt, key)):
            raise ValueError(f"Closeout changed frozen physics option {key}")
    for field in ("actuator_trnid", "actuator_gear", "actuator_gainprm", "actuator_biasprm",
                  "actuator_forcelimited", "actuator_ctrllimited", "actuator_ctrlrange"):
        if not np.array_equal(getattr(model, field), getattr(baseline, field)):
            raise ValueError(f"Closeout changed frozen actuator definition {field}")
    for index in range(18):
        expected = (np.array([-contract["joints"][index]["torque_peak_limit_nm"],
                               contract["joints"][index]["torque_peak_limit_nm"]])
                    if index in (6, 12) else baseline.actuator_forcerange[index])
        if not np.allclose(model.actuator_forcerange[index], expected, atol=1e-12, rtol=0):
            raise ValueError(f"Closeout actuator force limit mismatch at {index}")
    actual_motors = tuple(model.joint(int(model.actuator_trnid[i, 0])).name for i in range(model.nu))
    if actual_motors != MOTOR_ORDER or model.joint("beak_hinge").id == model.joint("beak_input_rotor").id:
        raise ValueError("Closeout motor and passive beak identity changed")
    validate_compiled_motor_limits(model, contract)
    geom_count = sum(1 for i in range(model.ngeom)
        if model.geom(i).name != "ground" and (model.geom_contype[i] or model.geom_conaffinity[i]))
    if geom_count != contact["leaf_count"] or geom_count > contact_leaf_limit(contract):
        raise ValueError("Compiled contact geometry differs from source manifest")
    support_vertices = 0
    for leaf in contact["leaves"]:
        geom = model.geom(leaf["name"]).id
        if model.body(int(model.geom_bodyid[geom])).name != leaf["owner"]:
            raise ValueError(f"Compiled contact owner mismatch: {leaf['name']}")
        if not (model.geom_contype[geom] or model.geom_conaffinity[geom]):
            raise ValueError(f"Declared contact leaf is disabled: {leaf['name']}")
        if not contact_shape_supported(model.geom_type[geom]):
            raise ValueError(f"Closeout collision-depth support requires mesh or box: {leaf['name']}")
        if (contract['closeout_native50'].get('diagnostic_profile') is not None
                or contract['closeout_native50'].get('production_profile') is not None
                or contract['candidate'] == CONTACT_LITE_CANDIDATE):
            count = 8
            if model.geom_type[geom] == mujoco.mjtGeom.mjGEOM_MESH:
                from .native_geometry315 import collision_mesh_vertices
                mesh = int(model.geom_dataid[geom])
                _, evidence = collision_mesh_vertices(model, mesh)
                count = evidence['support_vertex_count']
            limit = diagnostic_support_limit(leaf, contact)
            if contract['candidate'] == CONTACT_LITE_CANDIDATE and leaf['input_role'] == 'proxy':
                limit = 64
            if count > limit:
                raise ValueError(f"Compiled diagnostic leaf exceeds support budget: {leaf['name']} ({count})")
            support_vertices += count
    total_limit = (75000 if contract['candidate'] == CONTACT_LITE_CANDIDATE
                   else DIAGNOSTIC_PROFILE['total_support_vertices_limit'])
    if support_vertices > total_limit:
        raise ValueError('Compiled diagnostic contact exceeds total support budget')
    motion = json.loads(paths["motion"].read_text())
    active = motion["active_joints"]
    if [item["name"] for item in active] != list(MOTOR_ORDER):
        raise ValueError("Closeout active-motion order differs from motor order")
    for item in active:
        jid = model.joint(item["name"]).id
        if not np.allclose(model.jnt_range[jid], item["range_rad"], atol=1e-10, rtol=0):
            raise ValueError(f"Closeout motion range mismatch: {item['name']}")
    ledger = json.loads(paths["mci"].read_text())
    fk = json.loads(paths["fk_receipt"].read_text())
    for field,key in (('source_assembly','assembly'),('source_fk','fk_receipt')):
        if field in ledger and ledger[field].get('sha256') != contract['closeout_native50']['source_refs'][key]['sha256']:
            raise ValueError('Closeout bound MCI source mismatch: '+field)
    if (fk.get("assembly_sha256") != contract["closeout_native50"]["source_refs"]["assembly"]["sha256"]
            or fk.get("source_model_sha256") != contract["closeout_native50"]["source_refs"]["fk_xml"]["sha256"]):
        raise ValueError("FK receipt not bound to current assembly and 020 model")
    owners = ledger["owners"]
    if len(owners) != 21 or set(owners) != set(fk["bodies"]):
        raise ValueError("Closeout 21-owner MCI/FK inventory mismatch")
    shift = np.asarray(fk["source_to_runtime_translation_m"], float)
    if shift.shape != (3,) or not np.isfinite(shift).all():
        raise ValueError("Invalid source/runtime transform")
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    for name, owner in owners.items():
        bid = model.body(name).id
        body_fk = fk["bodies"][name]
        if (not np.allclose(data.xpos[bid], body_fk["position_world_m"], atol=1e-8, rtol=0)
                or not np.allclose(data.xmat[bid].reshape(3, 3), body_fk["rotation_world"], atol=1e-8, rtol=0)):
            raise ValueError(f"Closeout q0 body frame mismatch: {name}")
        rotation = data.ximat[bid].reshape(3, 3)
        inertia = rotation @ np.diag(model.body_inertia[bid]) @ rotation.T
        if (not np.isclose(model.body_mass[bid], owner["mass_kg"], atol=1e-9, rtol=0)
                or not np.allclose(data.xipos[bid], np.asarray(owner["com_world_m"]) + shift, atol=1e-8, rtol=0)
                or not np.allclose(inertia, owner["I_com_world_kg_m2"], atol=1e-9, rtol=0)):
            raise ValueError(f"Closeout q0 MCI mismatch: {name}")
    for name, expected in fk["joints"].items():
        jid = model.joint(name).id
        if (not np.allclose(data.xanchor[jid], expected["anchor_world_m"], atol=1e-8, rtol=0)
                or not np.allclose(data.xaxis[jid], expected["axis_world"], atol=1e-8, rtol=0)):
            raise ValueError(f"Closeout q0 joint frame mismatch: {name}")
    if set(fk["joints"]) != set(MOTOR_ORDER) | {"beak_hinge", "beak_coupler_link"}:
        raise ValueError("Closeout must bind all 18 motor axes and both passive axes")
    eq = model.equality("beak_distal_pin").id
    if (model.eq_type[eq] != mujoco.mjtEq.mjEQ_CONNECT
            or model.body(int(model.eq_obj1id[eq])).name != "beak_hinge"
            or model.body(int(model.eq_obj2id[eq])).name != "beak_coupler_link"
            or not np.allclose(model.eq_data[eq, :3], fk["beak_distal_pin_anchor_body1_m"], atol=1e-8, rtol=0)):
        raise ValueError("Closeout passive-beak connection or anchor mismatch")
    model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_AUTORESET)
    return CloseoutSourceRuntime(model, contract)


def load_beak_mapping(contract):
    """Import the hash-bound shared source mapping, never a copied geometry."""
    refs = contract["closeout_native50"]["source_refs"]
    path = _source(refs["beak_mapping_module"], "beak mapping module")
    module_name = "goose_beak_source_" + refs["beak_mapping_module"]["sha256"][:16]
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError("Cannot import hash-bound beak source mapping")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(module_name, None)
            raise
    package = _source(refs["fk_xml"], "FK XML").parent
    return sys.modules[module_name].BeakDriveMapping.from_package(package)


from .upstream_discrete import DiscreteSourceRuntime

class CloseoutSourceRuntime(DiscreteSourceRuntime):
    """Same 50Hz native loop, with rotor observations and analytic reset."""
    def __init__(self, model, contract):
        from .closeout_drive import CloseoutRigidNativeDrive
        self.model, self.contract = model, contract
        self.data = mujoco.MjData(model)
        self.drive = CloseoutRigidNativeDrive(contract, 1, device="cpu")
        self.qidx = np.array([model.joint(name).qposadr[0] for name in MOTOR_ORDER])
        self.vidx = np.array([model.joint(name).dofadr[0] for name in MOTOR_ORDER])
        self.motor_vids = model.jnt_dofadr[model.actuator_trnid[:, 0]]
        self.torso = model.body("torso").id
        self.commands = np.zeros(3)
        self.beak_mapping = load_beak_mapping(contract)
        self.reset()

    def reset(self):
        import torch
        if self.drive._pending_action is not None:
            raise RuntimeError('Preserve the pending closeout Tick before resetting physics')
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[2] += .002
        d.qpos[self.qidx] = self.drive.neutral.numpy()
        state = self.beak_mapping.from_input(float(d.qpos[self.qidx[5]]))
        d.qpos[m.joint("beak_hinge").qposadr[0]] = state.output_rad
        d.qpos[m.joint("beak_coupler_link").qposadr[0]] = state.coupler_rad
        self.drive.reset(torch.tensor([0]))
        mujoco.mj_forward(m, d)
        self.physics_integrations = self.controller_updates = 0
        return self.observations()
