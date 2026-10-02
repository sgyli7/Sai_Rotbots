#!/usr/bin/env python3
"""Coarse complete-module Gorilla sizing, with explicit unresolved physics."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/gorilla_v0_1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def native_mesh(part):
    faces=[[f[0],f[i],f[i+1]] for f in part['faces'] for i in range(1,len(f)-1)]
    return trimesh.Trimesh(part['vertices_world_m'],faces,process=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,default=ROBOT/'configs/internal_architecture_a_spec.json')
    parser.add_argument('--output',type=Path,default=ROBOT/'evidence/internal_architecture_a_budget.json')
    args=parser.parse_args();spec=json.loads(args.spec.read_text());scene_path=ROOT/spec['base_scene']
    assert sha(scene_path)==spec['base_scene_sha256'],'Base stage changed'
    scene=json.loads(scene_path.read_text());stock=[];armor=[]
    geometry_spec_path=ROOT/spec['base_geometry_spec']
    assert sha(geometry_spec_path)==scene['spec_sha256'],'Base geometry spec changed'
    for part in scene['parts']:
        role=part['role']
        if role not in ('primary_structure_candidate','primary_structure_socket_candidate','armor_surface','armor_cover'):continue
        m=native_mesh(part)
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):raise ValueError('Invalid material mesh: '+part['name'])
        density=[spec['stock_density_kg_m3']]*3 if role.startswith('primary_structure') else spec['armor_density_range_kg_m3']
        row={'id':part['name'],'role':role,'body':part['body'],'volume_m3':float(m.volume),'mass_range_kg':[float(m.volume*d) for d in density]}
        (stock if role.startswith('primary_structure') else armor).append(row)
    stock_mass=np.sum([r['mass_range_kg'] for r in stock],axis=0)
    armor_mass=np.sum([r['mass_range_kg'] for r in armor],axis=0)
    common=np.zeros(3);common_rows=[]
    for family,count in spec['common_modules'].items():
        masses=np.asarray(spec['module_classes'][family]['mass_range_kg'])*count;common+=masses
        common_rows.append({'family':family,'count':count,'mass_range_kg':masses.tolist()})
    routes={};g=spec['gravity_m_s2'];hyd=spec['hydraulic'];linear=spec['linear_drive'];energy=spec['energy'];thermal=spec['thermal']
    component_efficiencies=[linear['link_efficiency']*linear['screw_efficiency']*linear['reduction_efficiency']*motor*inverter
        for motor,inverter in zip(linear['motor_efficiency_range'],linear['inverter_efficiency_range'])]
    if not np.allclose(component_efficiencies,spec['routes']['linear_electric']['shaft_to_bus_efficiency_range'],rtol=0,atol=1e-10):
        raise ValueError('Linear electrical efficiency must equal its declared component product')
    cylinder_rows=[]
    for c in hyd['cylinders']:
        area=math.pi*c['bore_m']**2/4;annulus=area-math.pi*c['rod_m']**2/4
        cylinder_rows.append({**c,'push_force_at_pressure_N':[p*area for p in hyd['pressure_range_Pa']],
            'pull_force_at_pressure_N':[p*annulus for p in hyd['pressure_range_Pa']],
            'push_torque_at_nominal_pressure_and_lever_Nm':hyd['pressure_range_Pa'][1]*area*linear['effective_actuator_lever_range_m'][1]*linear['link_efficiency'],
            'pull_torque_at_nominal_pressure_and_lever_Nm':hyd['pressure_range_Pa'][1]*annulus*linear['effective_actuator_lever_range_m'][1]*linear['link_efficiency']})
    for name,route in spec['routes'].items():
        route_mass=np.zeros(3);rows=[]
        for family,count in route['modules'].items():
            masses=np.asarray(spec['module_classes'][family]['mass_range_kg'])*count;route_mass+=masses
            rows.append({'family':family,'count':count,'mass_range_kg':masses.tolist()})
        mass=stock_mass+armor_mass+common+route_mass;cases=[]
        for c in spec['load_cases']:
            values=[]
            for index,label in enumerate(('low','nominal','high')):
                support=(mass[index]+c['payload_kg'])*g*c['vertical_force_factor']
                torque=support*c['effective_leg_pitch_lever_m']
                peak_leg=torque*c['shaft_speed_rad_s']*c['simultaneous_high_load_axes']
                average_mechanical=peak_leg*c['motion_duty_fraction']+c['upper_body_mechanical_average_W']
                # Worst loss efficiency accompanies the high-mass sensitivity.
                efficiency=route['shaft_to_bus_efficiency_range'][2-index]
                aux=route['holding_and_aux_power_range_W'][index]
                bus_avg=average_mechanical/efficiency+aux
                bus_peak=(peak_leg+c['upper_body_mechanical_peak_W'])/efficiency+aux
                heat=bus_avg-average_mechanical
                flow=heat/(thermal['air_density_kg_m3']*thermal['air_cp_J_kgK']*thermal['air_temperature_rise_K'])
                force=torque/(linear['effective_actuator_lever_range_m'][1]*linear['link_efficiency'])
                rod_speed=linear['effective_actuator_lever_range_m'][1]*c['shaft_speed_rad_s']
                motor_torque=force*linear['screw_lead_m_rev']/(2*math.pi*linear['screw_efficiency']*linear['motor_to_screw_ratio']*linear['reduction_efficiency'])
                motor_rpm=rod_speed/linear['screw_lead_m_rev']*60*linear['motor_to_screw_ratio']
                values.append({'mass_sensitivity':label,'robot_stock_plus_module_budget_kg':float(mass[index]),
                    'single_support_normal_load_N':float(support),'representative_leg_gravity_support_pitch_Nm':float(torque),
                    'RV320E_rated_torque_utilization':float(torque/spec['rated_benchmarks']['RV320E_torque_Nm']),
                    'CSG65_rated_torque_utilization':float(torque/spec['rated_benchmarks']['CSG65_torque_Nm']),
                    'linear_required_force_N':float(force),
                    'linear_required_force_at_lever_range_N':[float(torque/(lever*linear['link_efficiency'])) for lever in linear['effective_actuator_lever_range_m']],
                    'linear_rod_speed_m_s':rod_speed,
                    'linear_motor_torque_Nm':float(motor_torque),'linear_motor_speed_rpm':motor_rpm,
                    'hydraulic_extension_flow_per_cylinder_L_min':{cyl['id']:math.pi*cyl['bore_m']**2/4*rod_speed*60000 for cyl in hyd['cylinders']},
                    'mechanical_average_W':float(average_mechanical),'bus_average_W':float(bus_avg),'bus_peak_concurrence_W':float(bus_peak),
                    'runtime_h_at_energy_sensitivity':float(energy['nominal_kWh_range'][index]*1000*energy['usable_fraction']/bus_avg),
                    'average_heat_to_remove_W':float(heat),'ideal_airflow_m3_h':float(flow*3600),
                    'air_speed_at_assumed_free_area_m_s':float(flow/thermal['intake_free_area_m2_assumption']),
                    'ideal_liquid_flow_L_min':float(heat/(thermal['liquid_cp_J_kgK']*thermal['liquid_temperature_rise_K'])*60),
                    'bus_peak_current_at_nominal_V_A':{str(v):float(bus_peak/v) for v in energy['candidate_bus_voltage_V']}})
            cases.append({'id':c['id'],'assumptions':c,'values':values})
        regen_mass=float(mass[1]+100)
        routes[name]={'robot_stock_plus_module_budget_range_kg':mass.tolist(),'route_module_rows':rows,'load_cases':cases,
            'separate_3000kg_pressure_demand_static_normal_load_N':[(float(m)+spec['separate_structural_pressure_case_kg'])*g for m in mass],
            'separate_pressure_scope':'Static demand including this gross stock budget; not payload rating, support capability, fixture/contact or strength acceptance.',
            'COM_lowering_recoverable_energy_J':regen_mass*g*energy['lowering_COM_m']*energy['recovery_efficiency'],
            'COM_lowering_average_regeneration_W':regen_mass*g*energy['lowering_COM_m']*energy['recovery_efficiency']/energy['regeneration_event_duration_s']}
    points=json.loads(geometry_spec_path.read_text())['points_world_m']
    segment_lengths={segment:float(np.linalg.norm(np.asarray(points['left_'+b])-points['left_'+a]))
        for segment,a,b in [('thigh','hip','knee'),('middle_shank','knee','fold'),('distal_shank','fold','ankle')]}
    report={'schema':'gorilla_internal_architecture_budget_v1','robot_id':'gorilla_v0_1',
        'base_scene_sha256':sha(scene_path),'spec_sha256':sha(args.spec),'script_sha256':sha(Path(__file__)),
        'base_geometry_spec_sha256':sha(geometry_spec_path),
        'research_sha256':sha(ROOT/spec['research']),'stock_rows':stock,'armor_rows':armor,
        'conditional_untrimmed_primary_stock_kg':stock_mass.tolist(),'conditional_armor_mass_range_kg':armor_mass.tolist(),
        'common_complete_module_rows':common_rows,'common_complete_module_mass_range_kg':common.tolist(),
        'routes':routes,'cylinder_ideal_area_results':cylinder_rows,'neutral_display_segment_lengths_m':segment_lengths,
        'linear_assumed_component_efficiency_product_range':component_efficiencies,
        'stock_and_module_mass_closed':False,'physics_accepted':False,'stable_physical_contract':False,'selected_route':None,
        'scope':'Coarse budget and sensitivity, not net mass, full joint load, feasible support, continuous drive, thermal acceptance or performance rating. Stock/module physical intersections, actual duty and actuator/package capabilities remain unresolved.',
        'red_lines':['Stock volume is untrimmed; no unproved mass credit or omitted complete modules.',
            'Actual axes, full articulated inertial/horizontal loads, contact and continuous lever sweep remain unverified.',
            'RV320E and CSG65 catalogue ratings are not complete-joint thermal qualifications.',
            'Cylinder length is compared to display links only; articulated mounts/remote transmission and sweep not closed.',
            'Electric linear and EHA module masses/continuous curves lack complete product validation.',
            'HV full-charge/regeneration/peak-current/protection system is not selected. Victron benchmark permits only two modules in series.',
            'Ideal airflow/liquid flow does not prove fan/core/duct pressure drop, cooling or recirculation performance.',
            'C15 foot fixed-side support/lock/bearing path is not closed.']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(args.output),'stock_kg':stock_mass.tolist(),'routes_kg':{k:v['robot_stock_plus_module_budget_range_kg'] for k,v in routes.items()},'segment_lengths_m':segment_lengths}))


if __name__=='__main__':main()
