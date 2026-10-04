use crate::plant::GoosePlant;
use crate::world::{PhysicsClockProfile, SimulationWorld};
use rapier3d::{
    math::{Rotation, Vector},
    prelude::*,
};
use serde_json::{Value, json};
use std::{collections::HashMap, env, fs, time::Instant};
#[derive(Debug, thiserror::Error)]
pub enum RobotError {
    #[error("invalid robot contract: {0}")]
    Contract(String),
    #[error("nonfinite: {0}")]
    NonFinite(&'static str),
}
mod basis;
mod builder;
mod control;
mod plant;
mod world;

fn vector(v: &Value) -> Vector {
    Vector::new(
        v[0].as_f64().unwrap() as f32,
        v[1].as_f64().unwrap() as f32,
        v[2].as_f64().unwrap() as f32,
    )
}
fn nominal_gravity(c: &Value, q: [f64; 18], quat: [f64; 4]) -> [f64; 5] {
    let joints = c["joints"].as_array().unwrap();
    let passive = c["passive_linkage_joints"].as_array().unwrap();
    let bodies: HashMap<_, _> = c["bodies"]
        .as_array()
        .unwrap()
        .iter()
        .map(|b| (b["name"].as_str().unwrap(), b))
        .collect();
    let mut pivots = HashMap::new();
    pivots.insert("torso", vector(&c["root_origin_at_zero_m"]));
    for j in joints.iter().take(6).chain(passive) {
        pivots.insert(
            j["name"].as_str().unwrap(),
            vector(&j["pivot_world_at_zero_m"]),
        );
    }
    let mut positions = HashMap::new();
    positions.insert("torso", Vector::ZERO);
    let mut rotations = HashMap::new();
    rotations.insert(
        "torso",
        Rotation::from_xyzw(
            quat[1] as f32,
            quat[2] as f32,
            quat[3] as f32,
            quat[0] as f32,
        )
        .normalize(),
    );
    let mut axes = Vec::new();
    let mut centers = Vec::new();
    let mut forces = Vec::new();
    for (i, j) in joints.iter().take(6).enumerate() {
        let n = j["name"].as_str().unwrap();
        let p = j["parent"].as_str().unwrap();
        let pr = rotations[p];
        let pos = positions[p] + pr * (pivots[n] - pivots[p]);
        positions.insert(n, pos);
        let axis = vector(&j["axis_parent"]);
        axes.push(pr * axis);
        let rotation = pr * Rotation::from_axis_angle(axis, q[i] as f32);
        rotations.insert(n, rotation);
        let b = bodies[n];
        centers.push(pos + rotation * vector(&b["com_local_m"]));
        forces.push(Vector::new(
            0.0,
            0.0,
            -9.81 * b["mass_kg"].as_f64().unwrap() as f32,
        ));
    }
    for j in passive {
        let n = j["name"].as_str().unwrap();
        let p = j["parent"].as_str().unwrap();
        let pr = rotations[p];
        let pos = positions[p] + pr * (pivots[n] - pivots[p]);
        positions.insert(n, pos);
        let index = joints
            .iter()
            .position(|v| v["name"] == j["mimic_joint"])
            .unwrap();
        let angle = j["mimic_multiplier"].as_f64().unwrap() * q[index]
            + j["mimic_offset_rad"].as_f64().unwrap();
        let rotation = pr * Rotation::from_axis_angle(vector(&j["axis_parent"]), angle as f32);
        rotations.insert(n, rotation);
        let b = bodies[n];
        centers.push(pos + rotation * vector(&b["com_local_m"]));
        forces.push(Vector::new(
            0.0,
            0.0,
            -9.81 * b["mass_kg"].as_f64().unwrap() as f32,
        ));
    }
    std::array::from_fn(|i| {
        let p = positions[joints[i]["name"].as_str().unwrap()];
        -(i..centers.len())
            .map(|k| (centers[k] - p).cross(forces[k]).dot(axes[i]) as f64)
            .sum::<f64>()
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    let plant: GoosePlant = serde_json::from_slice(&fs::read(&args[1])?)?;
    let c: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let control: control::GooseControlContract = serde_json::from_value(c.clone())?;
    use sha2::{Digest, Sha256};
    if format!("{:x}", Sha256::digest(fs::read(&args[2])?)) != plant.derived_contract_sha256
        || plant.model_sha256 != control.model_sha256
    {
        return Err("Plant/control identity mismatch".into());
    }
    let cfg = &c["contact_mapping"];
    if cfg["method"] != "whole_sole_native_manifold_backward_euler_v1"
        || (cfg["per_foot_stiffness_n_m"].as_f64().unwrap() - 140142.1824).abs() > 1e-8
        || cfg["per_foot_damping_n_s_m"] != 12.0
        || cfg["prediction_band_m"] != 0.01
    {
        return Err("Unknown material mapping requires a new receiver revision".into());
    }
    let mut simulation = SimulationWorld::new_with_profile(PhysicsClockProfile::Goose50);
    simulation
        .world
        .integration_parameters
        .num_internal_pgs_iterations = 32;
    simulation
        .world
        .integration_parameters
        .normalized_prediction_distance = 0.01;
    simulation
        .world
        .integration_parameters
        .warmstart_coefficient = 0.0;
    let floor = simulation.world.bodies.insert(RigidBodyBuilder::fixed());
    let ground = simulation.world.colliders.insert_with_parent(
        ColliderBuilder::halfspace(rapier3d::na::Unit::new_unchecked(Vector::Y))
            .friction(0.65)
            .collision_groups(InteractionGroups::new(
                Group::GROUP_1,
                Group::GROUP_1,
                InteractionTestMode::Or,
            )),
        floor,
        &mut simulation.world.bodies,
    );
    let robot = builder::GooseAssembly::build(&mut simulation, &plant, ground)?;
    let mut actuator = control::GooseActuatorState::new(&control)?;
    let mut trace = Vec::new();
    let scenario = args.get(4).map(String::as_str).unwrap_or("neutral");
    let ticks: usize = args.get(5).map(|s| s.parse().unwrap()).unwrap_or(500);
    for tick in 0..ticks {
        let state = robot.state(&simulation)?;
        let ff = nominal_gravity(&c, state.joint_position_rad, state.root_rotation_world_wxyz);
        let mut action = [0.0; 18];
        if scenario == "joint_motion" {
            let v = (tick as f64 * 0.02 * std::f64::consts::TAU * 0.25).sin();
            action[0] = 0.1 * v;
            action[5] = 0.1 * (1.0 - v) / 2.0;
            action[6] = 0.04 * v;
            action[12] = -0.04 * v;
        }
        if scenario == "jaw_full_range" {
            action[5] = ((tick as f64 * 0.02 * std::f64::consts::TAU * 0.125).sin() + 1.0) / 2.0;
        }
        let effort = actuator.update(
            &control,
            action,
            state.joint_position_rad,
            state.joint_velocity_rad_s,
            ff,
            1.0,
            false,
        )?;
        let start = Instant::now();
        robot.step(&mut simulation, effort.torque_nm)?;
        let ms = start.elapsed().as_secs_f64() * 1000.0;
        let state = match robot.state(&simulation) {
            Ok(v) => v,
            Err(e) => {
                let b = &simulation.world.bodies[robot.body_handles["torso"]];
                fs::write(
                    &args[3],
                    serde_json::to_vec_pretty(
                        &json!({"status":"failed","tick":tick+1,"error":e.to_string(),"raw_rotation_xyzw":b.rotation().to_array(),"root":b.translation().to_array(),"trace":trace}),
                    )?,
                )?;
                return Err(e.into());
            }
        };
        let up = -state.projected_gravity[2];
        let mut depth = 0.0_f64;
        let mut contacts = 0;
        for pair in simulation.world.narrow_phase.contact_pairs() {
            if pair.collider1 != ground && pair.collider2 != ground {
                continue;
            }
            for m in &pair.manifolds {
                for p in &m.points {
                    depth = depth.max(-p.dist as f64);
                    contacts += 1;
                }
            }
        }
        let mut post_depth = 0.0_f64;
        for shape in plant
            .colliders
            .iter()
            .filter(|g| g.name.ends_with("flexible_sole"))
        {
            let pose = simulation.world.bodies[robot.body_handles[&shape.body]].position()
                * builder::native_source_pose(shape.local_position_m, shape.local_rotation_wxyz)?;
            for v in shape
                .vertices_local_m
                .as_ref()
                .ok_or("Shoe hull points required")?
            {
                let corner =
                    Vector::from_array(basis::source_to_engine_vector(v.map(|x| x as f32)));
                post_depth = post_depth.max(-(pose * corner).y as f64);
            }
        }
        let observation = control.observation(
            &state,
            [0.0; 3],
            action,
            (tick + 1) as f64 * 0.02 * std::f64::consts::TAU * control.phase_frequency_hz,
        )?;
        let goal = control::TaskGoal {
            object_id: "probe_item".into(),
            position_world_m: [0.2, 0.1, 0.02],
            rotation_world_wxyz: [1.0, 0.0, 0.0, 0.0],
            placement_world_m: [0.4, -0.1, 0.02],
            valid: true,
        };
        let pickup = control.pickup_observation(
            observation,
            &state,
            &goal,
            control::PickupStage::Approach,
        )?;
        trace.push(json!({"observation":observation.to_vec(),"pickup_observation":pickup.to_vec(),"post_integration_sole_depth_m":post_depth,"pre_integration_contact_depth_m":depth,"observation_len":observation.len(),"action":action,"gravity_feedforward_nm":ff,"root_rotation_wxyz":state.root_rotation_world_wxyz,"tick":tick+1,"time_s":(tick+1) as f64*0.02,"upright":up,"root_position_m":state.root_position_world_m,
            "q":state.joint_position_rad,"qd":state.joint_velocity_rad_s,"torque_nm":effort.torque_nm,"normal_depth_m":depth,
            "contacts":contacts,"step_ms":ms,"jaw_pin_error_m":robot.jaw_pin_error_m(&simulation),"controller_updates":actuator.control_count,"integrations":tick+1}));
    }
    let mut native_support_count = 0;
    let mut native_shape_leaves = 0;
    let mut native_shapes = Vec::new();
    for (_, collider) in simulation.world.colliders.iter() {
        if collider.parent() == Some(floor) {
            continue;
        }
        let compound = collider
            .shape()
            .as_compound()
            .ok_or("Expected explicit one-child role compound")?;
        native_shape_leaves += compound.shapes().len();
        let group = &robot.collider_source_groups[native_shapes.len()];
        if group.len() != 1 {
            return Err("Role compound must contain one leaf".into());
        }
        let points = compound.shapes()[0]
            .1
            .as_convex_polyhedron()
            .ok_or("Expected convex role")?
            .points()
            .iter()
            .map(|p| basis::engine_to_source_vector(p.to_array()).map(f64::from))
            .collect::<Vec<_>>();
        native_shapes.push(json!({"name":group[0],"points_source_local_m":points}));
        for (_, shape) in compound.shapes() {
            native_support_count += if let Some(convex) = shape.as_convex_polyhedron() {
                convex.points().len()
            } else if shape.as_cuboid().is_some() {
                8
            } else {
                return Err("Unexpected native collision kind".into());
            };
        }
    }
    let report = json!({"native_shape_readback":native_shapes,"actual_native_shape_leaves":native_shape_leaves,"actual_native_support_points":native_support_count,"scenario":scenario,"schema":"goose_task_proxy_native_dynamic_probe_v1","candidate":plant.candidate_id,
        "source_geometry_count":robot.source_geometry_count,"native_collider_count":robot.collider_count,
        "collider_source_groups":robot.collider_source_groups,"jaw_constraints":1,"passive_springs":robot.passive_spring_count,"robot_bodies":robot.body_handles.len(),"body_measurements":robot.body_measurements,
        "native_dt_s":simulation.world.integration_parameters.dt,"native_solver_iterations":simulation.world.integration_parameters.num_solver_iterations,
        "physical_integrations":trace.len(),"trace":trace,"qualification":"measurements_require_M0_evaluator"});
    fs::write(&args[3], serde_json::to_vec_pretty(&report)?)?;
    println!(
        "Native articulated experiment completed; report {}",
        args[3]
    );
    Ok(())
}

#[cfg(test)]
mod foundation_tests;
