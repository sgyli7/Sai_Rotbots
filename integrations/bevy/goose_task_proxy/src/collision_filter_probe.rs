//! Deliberate-overlap diagnostics, separate from physical rollouts.
//! Use the production assembly, hook, joint flags and actually cooked hulls.

use super::*;
use serde_json::{Value, json};

fn setup(
    plant: &GoosePlant,
) -> Result<(SimulationWorld, GooseAssembly, ColliderHandle), RobotError> {
    let mut simulation = SimulationWorld::new_with_profile(PhysicsClockProfile::Goose50);
    let floor = simulation.world.bodies.insert(RigidBodyBuilder::fixed());
    let ground = simulation.world.colliders.insert_with_parent(
        ColliderBuilder::halfspace(na::Unit::new_unchecked(Vector::Y)).collision_groups(
            InteractionGroups::new(Group::GROUP_1, Group::GROUP_1, InteractionTestMode::Or),
        ),
        floor,
        &mut simulation.world.bodies,
    );
    let robot = GooseAssembly::build(&mut simulation, plant, ground)?;
    Ok((simulation, robot, ground))
}

fn role_handle(simulation: &SimulationWorld, robot: &GooseAssembly, body: &str) -> ColliderHandle {
    simulation.world.bodies[robot.body_handles[body]].colliders()[0]
}

fn place_hull(simulation: &mut SimulationWorld, handle: ColliderHandle, center: Vector) {
    let collider = &simulation.world.colliders[handle];
    let (child_pose, shape) = &collider.shape().as_compound().unwrap().shapes()[0];
    let points = shape.as_convex_polyhedron().unwrap().points();
    // The mean of all convex support points is strictly inside a full-volume hull.
    let mean = points.iter().copied().sum::<Vector>() / points.len() as f32;
    let local_center = *child_pose * mean;
    let body_pose = simulation.world.bodies[collider.parent().unwrap()].position();
    let pose = body_pose.inverse() * Pose::from_translation(center - local_center);
    simulation.world.colliders[handle].set_position_wrt_parent(pose);
}

fn leaf_world(simulation: &SimulationWorld, handle: ColliderHandle) -> (Pose, SharedShape) {
    let collider = &simulation.world.colliders[handle];
    let body = simulation.world.bodies[collider.parent().unwrap()].position();
    let pose = *body * *collider.position_wrt_parent().unwrap();
    if let Some(compound) = collider.shape().as_compound() {
        let (local, shape) = &compound.shapes()[0];
        (pose * *local, shape.clone())
    } else {
        (pose, collider.shared_shape().clone())
    }
}

fn measure(
    simulation: &mut SimulationWorld,
    robot: &GooseAssembly,
    first: ColliderHandle,
    second: ColliderHandle,
) -> Result<Value, RobotError> {
    for (handle, collider) in simulation.world.colliders.iter_mut() {
        collider.set_enabled(handle == first || handle == second);
    }
    let (pose1, shape1) = leaf_world(simulation, first);
    let (pose2, shape2) = leaf_world(simulation, second);
    // Parry 0.30.2's standalone support-map/halfspace query forwards pos12
    // without inversion. Use the canonical halfspace-first query for the raw
    // witness; the actual production narrow-phase pipeline below is unchanged.
    let raw_query = if shape2.as_halfspace().is_some() {
        rapier3d::parry::query::contact(&pose2, &*shape2, &pose1, &*shape1, 0.0)
    } else {
        rapier3d::parry::query::contact(&pose1, &*shape1, &pose2, &*shape2, 0.0)
    };
    let raw = raw_query
        .map_err(|_| invalid("Unsupported raw convex fixture query"))?
        .ok_or_else(|| {
            invalid(format!(
                "Filter fixture did not overlap: {:?} / {:?}; poses {:?} / {:?}",
                shape1.compute_aabb(&pose1),
                shape2.compute_aabb(&pose2),
                pose1,
                pose2
            ))
        })?;
    if raw.dist >= -1e-5 {
        return Err(invalid(
            "Filter fixture must have a real penetration witness",
        ));
    }
    // One native pipeline update. This is an intentionally impossible placement,
    // not a valid articulation pose, trajectory or hardware interference test.
    simulation.world.step_with_events(&robot.hooks, &());
    let pair = simulation.world.narrow_phase.contact_pair(first, second);
    let points = pair.map_or(0, |p| p.manifolds.iter().map(|m| m.points.len()).sum());
    let solver_contacts = pair.map_or(0, |p| {
        p.manifolds
            .iter()
            .map(|m| m.data.solver_contacts.len())
            .sum::<usize>()
    });
    let minimum_distance = pair.and_then(|p| {
        p.manifolds
            .iter()
            .flat_map(|m| m.points.iter())
            .map(|p| p.dist)
            .min_by(f32::total_cmp)
    });
    Ok(json!({"raw_unfiltered_distance_m":raw.dist,
        "native_contact_points":points,"native_solver_contacts":solver_contacts,
        "minimum_filtered_distance_m":minimum_distance,
        "collision_enabled":points > 0 && solver_contacts > 0}))
}

pub fn run(plant: &GoosePlant) -> Result<Value, RobotError> {
    let mut rows = Vec::new();
    for (index, first) in plant.colliders.iter().enumerate() {
        for second in plant.colliders.iter().skip(index + 1) {
            let (mut simulation, robot, _) = setup(plant)?;
            let a = role_handle(&simulation, &robot, &first.body);
            let b = role_handle(&simulation, &robot, &second.body);
            place_hull(&mut simulation, a, Vector::new(2.0, 3.0, 2.0));
            place_hull(&mut simulation, b, Vector::new(2.003, 3.001, 2.002));
            let result = measure(&mut simulation, &robot, a, b)
                .map_err(|e| invalid(format!("{} / {}: {e}", first.name, second.name)))?;
            rows.push(json!({"scope":"same_instance","first":first.name,
                "second":second.name,"measurement":result}));
        }
        for scope in ["ground", "object", "other_robot"] {
            let (mut simulation, robot, ground) = setup(plant)?;
            let a = role_handle(&simulation, &robot, &first.body);
            let center = Vector::new(2.0, if scope == "ground" { 0.0 } else { 3.0 }, 2.0);
            place_hull(&mut simulation, a, center);
            let b = match scope {
                "ground" => ground,
                "object" => {
                    let body = simulation
                        .world
                        .bodies
                        .insert(RigidBodyBuilder::fixed().translation(center));
                    simulation.world.colliders.insert_with_parent(
                        ColliderBuilder::ball(0.005).collision_groups(InteractionGroups::new(
                            Group::GROUP_1,
                            Group::GROUP_1,
                            InteractionTestMode::Or,
                        )),
                        body,
                        &mut simulation.world.bodies,
                    )
                }
                _ => {
                    let peer = GooseAssembly::build(&mut simulation, plant, ground)?;
                    let h = role_handle(&simulation, &peer, &first.body);
                    place_hull(
                        &mut simulation,
                        h,
                        center + Vector::new(0.003, 0.001, 0.002),
                    );
                    h
                }
            };
            let result = measure(&mut simulation, &robot, a, b)
                .map_err(|e| invalid(format!("{} / {scope}: {e}", first.name)))?;
            rows.push(json!({"scope":scope,"first":first.name,
                "second":if scope == "other_robot" {first.name.as_str()} else {scope},
                "measurement":result}));
        }
    }
    // A name-based/global mask would wrongly ignore these adjacent-role names
    // across two different robots. Keep these nine cross-instance pairs active.
    for (index, first) in plant.colliders.iter().enumerate() {
        for second in plant.colliders.iter().skip(index + 1) {
            let direct = plant.joints.iter().any(|j| {
                (j.parent == first.body && j.child == second.body)
                    || (j.parent == second.body && j.child == first.body)
            });
            let explicit = plant.exclusions.iter().any(|p| {
                (p[0] == first.body && p[1] == second.body)
                    || (p[0] == second.body && p[1] == first.body)
            });
            if !direct && !explicit {
                continue;
            }
            let (mut simulation, robot, ground) = setup(plant)?;
            let peer = GooseAssembly::build(&mut simulation, plant, ground)?;
            let a = role_handle(&simulation, &robot, &first.body);
            let b = role_handle(&simulation, &peer, &second.body);
            place_hull(&mut simulation, a, Vector::new(2.0, 3.0, 2.0));
            place_hull(&mut simulation, b, Vector::new(2.003, 3.001, 2.002));
            let result = measure(&mut simulation, &robot, a, b)?;
            rows.push(json!({"scope":"other_robot","first":first.name,
                "second":second.name,"measurement":result}));
        }
    }
    Ok(json!({"schema":"goose_native_collision_filter_probe_v1",
        "candidate_id":plant.candidate_id,"rows":rows,
        "scope":"Injected collider placements with original 21-body assembly, joint flags, masks and production hook; raw convex penetration checked before one native update per fixture. Not physical pose or dynamics qualification."}))
}
