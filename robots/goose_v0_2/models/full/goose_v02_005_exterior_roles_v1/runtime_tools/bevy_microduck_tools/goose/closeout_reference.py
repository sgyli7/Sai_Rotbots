"""Explicit external reference identity; this never changes the plant."""
from pathlib import Path
import copy
import json
import numpy as np
from .artifacts import sha256


def load_reference(model_path, contract_path, inputs):
    from .closeout_native50 import MOTOR_ORDER
    paths = {key: Path(inputs[key]).resolve(strict=True) for key in ('reference_action','validation_protocol')}
    for key,path in paths.items():
        if sha256(path) != inputs[key+'_sha256']:
            raise ValueError('External reference hash mismatch: '+key)
    protocol=json.loads(paths['validation_protocol'].read_text())
    reference=json.loads(paths['reference_action'].read_text())
    if (protocol.get('schema') != 'goose_owner_explicit_simulation_validation_protocol_v2'
            or protocol.get('public_action_semantics_changed') is not False
            or protocol.get('reference_is_external_policy_input') is not True
            or protocol.get('old_zero_action_standing_passed') is not False
            or protocol['reference']['sha256'] != inputs['reference_action_sha256']
            or sha256(Path(model_path)) != protocol['plant_model_sha256']):
        raise ValueError('External reference protocol/plant identity mismatch')
    archive=paths['validation_protocol'].parent/'archive.json'
    archived=json.loads(archive.read_text()) if archive.exists() else None
    def resolve(row):
        if archived is not None:
            candidate=(archive.parent/archived[row['sha256']]).resolve(strict=True)
            if not candidate.is_relative_to(archive.parent):
                raise ValueError('Reference archive escapes package')
        else:
            candidates=[root/row['path'] for root in paths['validation_protocol'].parents]
            candidate=next((x for x in candidates if x.is_file()),None)
            if candidate is None:
                raise ValueError('Missing bound reference evidence: '+row['path'])
        if sha256(candidate) != row['sha256']:
            raise ValueError('Bound reference evidence changed: '+row['path'])
        return candidate
    files={key:resolve(protocol[key]) for key in ('reference_controller_source',
           'first_standing_evidence','preserved_zero_action_failure','source_assembly','source_mci','source_fk')}
    kind=protocol.get('reference_kind','constant_action_v1')
    if kind == 'ap_pitch_feedback_v1':
        for key in ('constant_reference','first_cpu_evidence','preserved_constant_drop_failure','previous_protocol'):
            files[key]=resolve(protocol[key])
    elif kind != 'constant_action_v1':
        raise ValueError('Unsupported external reference kind')
    contract=json.loads(Path(contract_path).read_text())
    if archived is not None:
        original=resolve({'path':'original_contract.json','sha256':protocol['plant_contract_sha256']})
        expected=json.loads(original.read_text())
        def normalized(value):
            value=copy.deepcopy(value)
            metadata=value['closeout_native50']
            from .closeout_native50 import PRODUCTION_CANDIDATE
            if value.get('candidate') == PRODUCTION_CANDIDATE:
                for key in ('candidate','candidate_id','training_ready','status'):
                    if key in expected: value[key]=expected[key]
                    else: value.pop(key,None)
                for key in ('engineering_entry','qualified_scope'):
                    if key in expected['qualification']: value['qualification'][key]=expected['qualification'][key]
                    else: value['qualification'].pop(key,None)
                for key in ('production_profile','adoption_files','production_adoption','adopted_from_contract','runtime_requirements'):
                    metadata.pop(key,None)
                metadata['diagnostic_profile']=expected['closeout_native50']['diagnostic_profile']
            metadata.pop('portable_gravity_root',None)
            metadata.pop('_resolved_gravity_source_root',None)
            for row in metadata['source_refs'].values(): row.pop('path',None)
            return value
        if normalized(contract) != normalized(expected):
            raise ValueError('Relocated reference plant contract semantics changed')
        files['original_contract']=original
    elif sha256(Path(contract_path)) != protocol['plant_contract_sha256']:
        raise ValueError('External reference contract identity mismatch')
    for key,source in (('source_assembly','assembly'),('source_mci','mci'),('source_fk','fk_receipt')):
        if contract['closeout_native50']['source_refs'][source]['sha256'] != protocol[key]['sha256']:
            raise ValueError('Reference source cohort mismatch: '+source)
    order=list(MOTOR_ORDER)
    constant=(json.loads(files['constant_reference'].read_text())
              if kind == 'ap_pitch_feedback_v1' else reference)
    action=np.asarray(constant['constant_normalized_action'],dtype=float)
    first=json.loads(files['first_standing_evidence'].read_text())
    old=json.loads(files['preserved_zero_action_failure'].read_text())
    common_bad=(contract['joint_order'] != order or action.shape != (18,)
            or not np.isfinite(action).all() or np.any(np.abs(action)>1)
            or reference.get('plant_or_action_semantics_changed') is not False
            or first.get('baseline_id') != reference['baseline_id']
            or first.get('controller_source_sha256') != protocol['reference_controller_source']['sha256']
            or not old.get('failure'))
    if kind == 'constant_action_v1':
        bad=(first.get('standing_baseline_passed') is not True or first.get('CPU_integrations') != 100
             or first.get('static_reference_sha256') != inputs['reference_action_sha256'])
    else:
        old_drop=json.loads(files['preserved_constant_drop_failure'].read_text())
        bad=(first.get('all_three_cases_passed') is not True or first.get('CPU_integrations') != 300
             or first.get('feedback_parameters_sha256') != inputs['reference_action_sha256']
             or first.get('constant_reference_sha256') != protocol['constant_reference']['sha256']
             or not old_drop.get('failure')
             or any(first.get('case_results',{}).get(case,{}).get('integrations') != 100
                    for case in ('standing','drop_50mm','reinitialize')))
    if common_bad or bad:
        raise ValueError('Invalid bounded external reference or preserved evidence')
    identity={'baseline_id':reference['baseline_id'],'protocol_id':protocol['protocol_id'],
        'reference_action_sha256':inputs['reference_action_sha256'],
        'validation_protocol_sha256':inputs['validation_protocol_sha256'],
        'controller_source_sha256':protocol['reference_controller_source']['sha256'],
        'joint_order':order,'external_policy_input':True,'reference_kind':kind}
    loaded={'action':action,'identity':identity,'files':files,'paths':paths,'parameters':reference,'contract':contract}
    if kind == 'ap_pitch_feedback_v1':
        import importlib.util
        spec=importlib.util.spec_from_file_location('goose_frozen_external_'+identity['controller_source_sha256'],files['reference_controller_source'])
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        loaded['controller']=module.reference_action
    return loaded


def archive_reference(model_path, contract_path, inputs, destination):
    import shutil
    loaded=load_reference(model_path,contract_path,inputs)
    destination=Path(destination);destination.mkdir()
    files={**loaded['files'],**loaded['paths']}
    files.setdefault('original_contract',Path(contract_path))
    index={}
    for key,source in files.items():
        name=key+source.suffix
        shutil.copy2(source,destination/name)
        index[sha256(source)]=name
    (destination/'archive.json').write_text(json.dumps(index,indent=2)+'\n')
    return {**inputs,'reference_action':destination/'reference_action.json',
            'validation_protocol':destination/'validation_protocol.json'}


def evaluate_reference(loaded, qpos, qvel):
    if 'controller' in loaded:
        action,state=loaded['controller'](np.asarray(qpos),np.asarray(qvel),loaded['action'],
                                         loaded['contract'],loaded['parameters'])
    else:
        action,state=loaded['action'].copy(),{}
    if action.shape != (18,) or not np.isfinite(action).all() or np.any(np.abs(action)>1):
        raise ValueError('External controller produced an invalid public action')
    return action,state
