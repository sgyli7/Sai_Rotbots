"""Portable, byte-preserving source bundle for the independent closeout plant.

Packaging performs no compilation, integration, policy work or qualification.
The dependency environment remains separately pinned by the source contract.
"""
from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
from pathlib import Path
import shutil

from .artifacts import sha256
from .closeout_native50 import (validate_source_contract, PRODUCTION_CANDIDATE,
                               PRODUCTION_PROFILE, CANDIDATE, DIAGNOSTIC_PROFILE,PRODUCTION_RUNTIME_REQUIREMENTS)

ADOPTION_CHECKS = {'source_void','compiled_contact','mci_actuation',
                   'cpu_native50','gpu_native50','portable'}


REFERENCE_PROTOCOL_SHA256 = 'b3048c7cd934928b163fa6e8ef07098fc6d91f04fcd2e647ca111dc7881b5242'
DYNAMIC_REFERENCE_PROTOCOL_SHA256 = '85df7e7b4a798de6ca1138230344043e38be281c5b0121da37f98c64b859fb7a'


def validate_reference_adoption(approval, resolve, model_sha, contract_sha, source_shas):
    external=approval.get('external_reference')
    if external is None:
        return None,[]
    protocol_sha=external.get('validation_protocol',{}).get('sha256')
    if protocol_sha not in (REFERENCE_PROTOCOL_SHA256,DYNAMIC_REFERENCE_PROTOCOL_SHA256):
        raise ValueError('Unapproved external-reference validation protocol')
    files={key:resolve(external[key]) for key in ('validation_protocol','reference_action',
           'controller_source','original_zero_action_failure')}
    protocol=json.loads(files['validation_protocol'].read_text())
    reference=json.loads(files['reference_action'].read_text())
    expected={'baseline_id':reference['baseline_id'],'protocol_id':protocol['protocol_id'],
        'reference_action_sha256':protocol['reference']['sha256'],
        'validation_protocol_sha256':protocol_sha,
        'controller_source_sha256':protocol['reference_controller_source']['sha256']}
    if (protocol['plant_model_sha256'] != model_sha or protocol['plant_contract_sha256'] != contract_sha
            or external.get('baseline_id') != expected['baseline_id']
            or external['reference_action']['sha256'] != expected['reference_action_sha256']
            or external['controller_source']['sha256'] != expected['controller_source_sha256']
            or external['original_zero_action_failure']['sha256'] != protocol['preserved_zero_action_failure']['sha256']
            or not json.loads(files['original_zero_action_failure'].read_text()).get('failure')
            or protocol['source_assembly']['sha256'] != source_shas['assembly']
            or protocol['source_mci']['sha256'] != source_shas['mci']
            or protocol['source_fk']['sha256'] != source_shas['fk_receipt']
            or external.get('qualification_scope') != 'simulation_with_bound_external_reference'
            or external.get('old_zero_action_standing_passed') is not False):
        raise ValueError('External reference adoption identity or preserved failure mismatch')
    if protocol_sha == DYNAMIC_REFERENCE_PROTOCOL_SHA256:
        if external.get('reference_kind') != 'ap_pitch_feedback_v1' or protocol.get('reference_kind') != 'ap_pitch_feedback_v1':
            raise ValueError('Dynamic reference kind mismatch')
        for key,source_key in (('constant_reference','constant_reference'),
                               ('original_constant_drop_failure','preserved_constant_drop_failure')):
            if external.get(key,{}).get('sha256') != protocol[source_key]['sha256']:
                raise ValueError('Dynamic reference baseline or preserved drop failure mismatch')
            files[key]=resolve(external[key])
        if not json.loads(files['original_constant_drop_failure'].read_text()).get('failure'):
            raise ValueError('Preserved constant drop failure is missing')
        expected['reference_kind']='ap_pitch_feedback_v1'
        backend=approval.get('runtime_backend',{})
        if backend.get('execution_mode')!='uncaptured':raise ValueError('This production entry requires the explicitly qualified uncaptured backend')
        for key in ('numerical_acceptance','overlay_manifest','collision_module'):
            files['backend_'+key]=resolve(backend[key])
        if backend['numerical_acceptance']['sha256']!='c6a9b21f02b55b10298c922b7472a096130e97caf3f9ec4af3bf82cc3ac330f8':
            raise ValueError('Wrong predeclared numerical acceptance')
    return expected,[(approval['runtime_backend'][key.removeprefix('backend_')]if key.startswith('backend_')else external[key],path)for key,path in files.items()]


def validate_adoption_document(approval, resolve, model_sha, contract_sha, source_shas):
    """Check Owner's immutable decision and six same-object evidence receipts."""
    if (approval.get('schema') != 'goose_closeout_controlled_adoption_v1'
            or approval.get('approved') is not True or not approval.get('owner')
            or approval.get('target_candidate') != PRODUCTION_CANDIDATE
            or approval.get('production_profile') != PRODUCTION_PROFILE
            or approval.get('scope') != 'native50_simulation_training_entry'
            or approval.get('source_model', {}).get('sha256') != model_sha
            or approval.get('source_contract', {}).get('sha256') != contract_sha
            or approval.get('source_sha256s') != source_shas
            or approval.get('accepted_nominal_mci', {}).get('ledger_sha256') != source_shas['mci']
            or approval.get('accepted_nominal_mci', {}).get('inherited_assumptions_retained') is not True):
        raise ValueError('Owner adoption identity, scope or nominal MCI acknowledgment mismatch')
    receipts = approval.get('receipts', {})
    if set(receipts) != ADOPTION_CHECKS:
        raise ValueError('Adoption requires exactly six complete evidence classes')
    external,resolved=validate_reference_adoption(approval,resolve,model_sha,contract_sha,source_shas)
    for key, ref in receipts.items():
        path = resolve(ref)
        resolved.append((ref,path))
        receipt = json.loads(path.read_text())
        if (receipt.get('schema') != 'goose_closeout_adoption_check_v1'
                or receipt.get('check_id') != key or receipt.get('passed') is not True
                or receipt.get('model_sha256') != model_sha
                or receipt.get('contract_sha256') != contract_sha
                or receipt.get('source_sha256s') != source_shas):
            raise ValueError('Missing, failed or mismatched adoption receipt: '+key)
        underlying = receipt.get('actual_evidence', [])
        if not underlying:
            raise ValueError('Adoption receipt lacks actual evidence: '+key)
        for evidence in underlying:
            resolved.append((evidence,resolve(evidence)))
        details = receipt.get('details', {})
        required = {
            'source_void':('all_required_source_and_void_gates_passed',),
            'compiled_contact':('compiled_functional_geometry_passed',),
            'mci_actuation':('world_mci_and_18_axis_readback_passed',),
            'cpu_native50':('finite_clock_capacity_passed','zero_action_standing'),
            'gpu_native50':('finite_clock_capacity_passed','same_input_reference','precision_passed'),
            'portable':('relocated','cpu_load_step_passed','no_external_source_paths'),
        }[key]
        if external is not None and key == 'cpu_native50':
            required=('finite_clock_capacity_passed','standing_with_bound_reference')
            if (details.get('zero_action_standing') is not False
                    or details.get('original_zero_action_failure') != approval['external_reference']['original_zero_action_failure']):
                raise ValueError('Reference standing cannot relabel original zero-action failure')
        if external is not None and key in ('cpu_native50','gpu_native50','portable'):
            bound=details.get('external_reference',{})
            if any(bound.get(name) != value for name,value in external.items()):
                raise ValueError('Measured receipt external reference mismatch: '+key)
        if any(details.get(flag) is not True for flag in required):
            raise ValueError('Required measured acceptance missing: '+key)
        if key == 'cpu_native50':
            cases = details.get('case_integrations', {})
            if (details.get('physics_dt_s') != .02
                    or set(cases) != {'standing','drop_50mm','reinitialize'}
                    or any(type(count) is not int or count < 100 for count in cases.values())):
                raise ValueError('CPU adoption requires actual100-tick cases at20ms')
        if key == 'gpu_native50':
            if (details.get('physics_dt_s') != .02 or not details.get('measured_error_bounds')
                    or details.get('graph_capture_used') not in (True,False)
                    or details.get('graph_capture_used') is True
                    and details.get('graph_capture_control_comparison_passed') is not True):
                raise ValueError('GPU adoption needs measured precision and explicit graph control')
            if external is not None and external.get('reference_kind') == 'ap_pitch_feedback_v1':
                if (details.get('reference_mode') != 'exact_CPU_standing_action_trace_replay'
                        or details.get('same_input_verified_each_tick') is not True
                        or not details.get('cpu_action_trace',{}).get('sha256')):
                    raise ValueError('Dynamic reference GPU needs exact CPU action replay evidence')
                resolved.append((details['cpu_action_trace'],resolve(details['cpu_action_trace'])))
    return resolved


def adopt_bundle(approval_path, approval_sha256, destination):
    """Root-controlled adoption; preserve tested model/source bytes and old IDs."""
    from .closeout_native50 import _source
    approval_path = Path(approval_path).resolve(strict=True)
    if sha256(approval_path) != approval_sha256:
        raise ValueError('Owner approval hash changed')
    approval = json.loads(approval_path.read_text())
    resolve = lambda ref:_source(ref,'Owner adoption input',approval_path.parent)
    model, source_contract = (resolve(approval[key]) for key in ('source_model','source_contract'))
    contract, _, _ = validate_source_contract(model,source_contract)
    if (contract['candidate'] != CANDIDATE
            or contract['closeout_native50'].get('diagnostic_profile') != DIAGNOSTIC_PROFILE):
        raise ValueError('Adoption must start from the complete checked diagnostic candidate')
    source_shas = {name:ref['sha256'] for name,ref in contract['closeout_native50']['source_refs'].items()}
    inputs = validate_adoption_document(approval,resolve,sha256(model),sha256(source_contract),source_shas)
    destination = Path(destination).resolve()
    reference_inputs=None
    if approval.get('external_reference') is not None:
        external=approval['external_reference']
        reference_inputs={key:resolve(external[key]) for key in ('reference_action','validation_protocol')}
        reference_inputs.update({key+'_sha256':external[key]['sha256'] for key in ('reference_action','validation_protocol')})
    export_bundle(model,source_contract,destination,reference_inputs=reference_inputs)
    new_path = destination/'contract.json'
    new = json.loads(new_path.read_text())
    identity = new['closeout_native50']
    identity.pop('diagnostic_profile',None)
    identity['production_profile'] = PRODUCTION_PROFILE
    identity['runtime_requirements'] = copy.deepcopy(PRODUCTION_RUNTIME_REQUIREMENTS)
    archive = {}
    for ref,path in [({'sha256':approval_sha256},approval_path),
                     ({'sha256':sha256(source_contract)},source_contract),*inputs]:
        relative = 'sources/adoption/'+ref['sha256']+path.suffix
        target = destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copy2(path,target)
        archive[ref['sha256']] = relative
    identity['adoption_files'] = archive
    identity['production_adoption'] = {'path':archive[approval_sha256],'sha256':approval_sha256}
    identity['adopted_from_contract'] = {'path':archive[sha256(source_contract)],'sha256':sha256(source_contract)}
    new.update(candidate=PRODUCTION_CANDIDATE,candidate_id=PRODUCTION_CANDIDATE,
        training_ready=True,status='OWNER_ADOPTED_NATIVE50_SIMULATION_TRAINING_ENTRY')
    new['qualification']['engineering_entry'] = True
    new['qualification']['qualified_scope'] = 'native50_simulation_training_entry'
    new_path.write_text(json.dumps(new,indent=2)+'\n')
    validate_source_contract(destination/'robot.xml',new_path)
    manifest = {'schema':'goose_closeout_adopted_bundle_v1','candidate':PRODUCTION_CANDIDATE,
        'approval_sha256':approval_sha256,'training_ready':True,'learned_policy_qualified':False,
        'external_reference':approval.get('external_reference'),
        'model_bytes_unchanged':sha256(destination/'robot.xml') == sha256(model),
        'files':{p.relative_to(destination).as_posix():sha256(p) for p in destination.rglob('*')
                 if p.is_file() and p.name != 'bundle_manifest.json'}}
    (destination/'bundle_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def export_bundle(model_path: Path, contract_path: Path, destination: Path, *, reference_inputs=None, precision_acceptance=None):
    contract, sources, _ = validate_source_contract(model_path, contract_path)
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Preserve the existing source bundle')
    # Inspect the extra four-bar dependencies before creating any output.
    fk_root = sources['fk_xml'].parent
    manifest_path = fk_root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    declared = {row['path']: row['sha256'] for row in manifest['files']}
    if len(declared) != len(manifest['files']):
        raise ValueError('Ambiguous four-bar source manifest')
    attachments = {}
    for name in ('physical_contract.json', 'runtime_interface.json', 'robot.xml',
                 'parent_runtime_adapter.py', 'runtime_adapter.py'):
        path = fk_root / name
        if sha256(path) != declared.get(name):
            raise ValueError('Four-bar source attachment changed: '+name)
        attachments[name] = path
    if (sha256(attachments['robot.xml']) != sha256(sources['fk_xml'])
            or sha256(attachments['physical_contract.json']) != sha256(sources['hardware_contract'])):
        raise ValueError('Four-bar attachment is not the bound FK/hardware source')
    baseline = json.loads(sources['baseline_contract'].read_text())
    gravity_relative = 'src/sai_agent/goose/stage_one_gravity.py'
    gravity_root = contract['closeout_native50'].get('_resolved_gravity_source_root',
        contract['source_checkpoint']['source_root'])
    gravity_source = Path(gravity_root)/gravity_relative
    if sha256(gravity_source) != contract['source_checkpoint']['source_module_sha256'][gravity_relative]:
        raise ValueError('Nominal gravity source identity changed')
    baseline_assets = {}
    for relative, digest in baseline['asset_sha256'].items():
        path = (sources['baseline_model'].parent / relative).resolve(strict=True)
        if (Path(relative).is_absolute() or '..' in Path(relative).parts
                or not path.is_relative_to(sources['baseline_model'].parent)
                or sha256(path) != digest):
            raise ValueError('Baseline geometry identity changed: '+relative)
        baseline_assets[relative] = path
    destination.mkdir(parents=True)

    def put(source, relative):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256(target) != sha256(source):
            raise ValueError('Conflicting portable source destination: '+str(relative))
        shutil.copy2(source, target)
        return target.relative_to(destination).as_posix()

    new = copy.deepcopy(contract)
    new['closeout_native50'].pop('_resolved_gravity_source_root', None)
    new['closeout_native50']['portable_gravity_root'] = 'sources/gravity'
    for name, path in sources.items():
        if name == 'fk_xml':
            relative = Path('sources/fk/robot.xml')
        elif name == 'hardware_contract':
            relative = Path('sources/fk/physical_contract.json')
        elif name == 'baseline_model':
            relative = Path('sources/baseline/robot.xml')
        elif name == 'baseline_contract':
            relative = Path('sources/baseline/contract.json')
        else:
            relative = Path('sources') / name / path.name
        new['closeout_native50']['source_refs'][name]['path'] = put(path, relative)
    put(manifest_path, Path('sources/fk/manifest.json'))
    for name, path in attachments.items():
        put(path, Path('sources/fk') / name)
    for relative, path in baseline_assets.items():
        put(path, Path('sources/baseline') / relative)
    put(gravity_source, Path('sources/gravity') / gravity_relative)
    for digest, relative in contract['closeout_native50'].get('adoption_files', {}).items():
        source = (Path(contract_path).resolve().parent/relative).resolve(strict=True)
        if sha256(source) != digest:
            raise ValueError('Archived adoption evidence changed')
        put(source,Path(relative))
    put(Path(model_path), Path('robot.xml'))
    for relative in contract['asset_sha256']:
        put(Path(model_path).parent / relative, Path(relative))
    target_contract = destination / 'contract.json'
    target_contract.write_text(json.dumps(new, indent=2)+'\n')
    validate_source_contract(destination/'robot.xml', target_contract)
    # Snapshot the actual runtime code, rather than leaving a PYTHONPATH link
    # to a mutable checkout. External engine wheels remain pinned separately.
    tested_snapshot = Path(model_path).resolve().parent/'runtime_tools/bevy_microduck_tools/goose'
    package = tested_snapshot if tested_snapshot.is_dir() else Path(__file__).resolve().parent
    put(package.parent/'__init__.py', Path('runtime_tools/bevy_microduck_tools/__init__.py'))
    for module in package.glob('*.py'):
        put(module, Path('runtime_tools/bevy_microduck_tools/goose')/module.name)
    from .upstream_discrete_mjlab import VERSIONS
    dependencies = {name: importlib.metadata.version(name)
                    for name in (*VERSIONS, 'torch', 'numpy', 'scipy')}
    (destination/'runtime_dependencies.json').write_text(json.dumps({
        'python':'3.12', 'installed_snapshot':dependencies, 'required_engine_versions':VERSIONS,
        'environment_included':False}, indent=2)+'\n')
    (destination/'run_admission.py').write_text(
        'from pathlib import Path\nimport sys\n'
        'root = Path(__file__).resolve().parent\n'
        'sys.path.insert(0, str(root / "runtime_tools"))\n'
        'from bevy_microduck_tools.goose.closeout_admission import main\n'
        'if __name__ == "__main__":\n    main()\n')
    if reference_inputs is not None:
        from .closeout_reference import archive_reference
        archive_reference(model_path,contract_path,reference_inputs,destination/'reference_inputs')
    if precision_acceptance is not None:
        put(Path(precision_acceptance['path']),Path('validation/gpu_precision_acceptance_001.json'))
    files = {p.relative_to(destination).as_posix(): sha256(p)
             for p in destination.rglob('*') if p.is_file()}
    receipt = {'schema': 'goose_closeout_portable_source_bundle_v1',
        'candidate': contract['candidate'], 'source_contract_sha256': sha256(Path(contract_path)),
        'files': files, 'physics_integrations': 0, 'optimizer_updates': 0,
        'training_ready': contract.get('training_ready',False),
        'status': ('OWNER_ADOPTED_PORTABLE_SOURCE_BYTES' if contract['candidate'] == PRODUCTION_CANDIDATE
                   else 'PORTABLE_SOURCE_BYTES_ONLY_NOT_DYNAMICALLY_ADMITTED')}
    (destination/'bundle_manifest.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--adopt',type=Path,help='Hash-bound Owner approval JSON')
    parser.add_argument('--approval-sha256')
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    if args.adopt:
        if not args.approval_sha256 or args.model or args.contract:
            parser.error('--adopt requires --approval-sha256 and carries its own source paths')
        receipt = adopt_bundle(args.adopt,args.approval_sha256,args.destination)
    else:
        if args.model is None or args.contract is None:
            parser.error('--model and --contract are required for diagnostic export')
        receipt = export_bundle(args.model, args.contract, args.destination)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'files'}))


if __name__ == '__main__':
    main()
