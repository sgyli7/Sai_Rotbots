//! Source-derived Goose bodies, joint springs, collision masks and four-bar pin.

use std::collections::{BTreeMap, HashMap, HashSet};

use crate::{
    RobotError,
    basis::{
        engine_to_source_rotation, engine_to_source_vector, source_to_engine_rotation,
        source_to_engine_vector,
    },
    plant::{GooseBody, GooseCollider, GoosePlant},
};
use rapier3d::{
    math::{Matrix, Pose, Rotation, Vector},
    na,
    prelude::*,
};
use serde::Serialize;

use crate::control::GooseNativeState;
use crate::world::{BodyTorque, PhysicsClockProfile, SimulationError, SimulationWorld};
use rapier3d::{geometry::ExperimentalNormalSpring, pipeline::ContactModificationContext};

/// Measurements compare the actual backend body to the full source tensor.
#[derive(Debug, Serialize)]
pub struct GooseBodyMeasurement {
    pub name: String,
    pub mass_kg: f32,
    pub mass_error_kg: f64,
    pub com_error_m: f64,
    pub full_inertia_relative_error: f64,
}

struct JointMapping {
    handle: MultibodyJointHandle,
    parent: RigidBodyHandle,
    child: RigidBodyHandle,
    coordinate: usize,
    axis_parent: Vector,
    active_axis: Option<usize>,
    feedback_axis: Option<usize>,
}

/// Handles remain bound to the caller's world; no second world or FK controller.
pub struct GooseAssembly {
    pub body_handles: HashMap<String, RigidBodyHandle>,
    pub body_measurements: Vec<GooseBodyMeasurement>,
    pub jaw_loop_handle: ImpulseJointHandle,
    pub passive_spring_count: usize,
    pub collider_count: usize,
    pub source_geometry_count: usize,
    pub collider_source_groups: Vec<Vec<String>>,
    joints: Vec<JointMapping>,
    hooks: GooseCollisionHooks,
    pin_local_coupler: Vector,
    pin_local_jaw: Vector,
    coupler: RigidBodyHandle,
    jaw: RigidBodyHandle,
}

/// Only the source's explicit exclusions are added to native adjacent filtering.
struct GooseCollisionHooks {
    ground: ColliderHandle,
    feet: HashSet<RigidBodyHandle>,
    excluded: HashSet<[(u32, u32); 2]>,
}

impl PhysicsHooks for GooseCollisionHooks {
    fn modify_solver_contacts(&self, context: &mut ContactModificationContext) {
        if context.collider1 != self.ground && context.collider2 != self.ground {
            return;
        }
        if ![context.rigid_body1, context.rigid_body2]
            .iter()
            .flatten()
            .any(|b| self.feet.contains(b))
        {
            return;
        }
        if !context.solver_contacts.is_empty() {
            let n = context.solver_contacts.len() as f32;
            *context.experimental_normal_spring = Some(ExperimentalNormalSpring {
                stiffness_n_m: 6.0 * 23357.0304 / n,
                damping_n_s_m: 12.0 / n,
            });
        }
    }
    fn filter_contact_pair(&self, context: &PairFilterContext<'_>) -> Option<SolverFlags> {
        if let (Some(first), Some(second)) = (context.rigid_body1, context.rigid_body2) {
            if self.excluded.contains(&ordered_pair(first, second)) {
                return None;
            }
        }
        Some(SolverFlags::COMPUTE_IMPULSES)
    }
}

impl GooseAssembly {
    /// Construct the explicit task proxy and its versioned sole contact law.
    pub fn build(
        simulation: &mut SimulationWorld,
        plant: &GoosePlant,
        ground: ColliderHandle,
    ) -> Result<Self, RobotError> {
        if plant.schema != "goose_task_proxy_plant_v1"
            || plant.candidate_id != "goose_task_proxy_11_v1"
            || plant.bodies.len() != 21
            || plant.colliders.len() != 11
            || plant.physics_hz != 50
        {
            return Err(invalid("Explicit 11-leaf task proxy identity required"));
        }
        if simulation.clock_profile() != PhysicsClockProfile::Goose50 {
            return Err(invalid(
                "Goose needs the explicit single-step 50 Hz world profile",
            ));
        }
        plant.validate()?;
        let world = &mut simulation.world;
        let lift = Vector::Y * 0.002;
        let mut poses = HashMap::new();
        let mut shape_groups: BTreeMap<
            (String, u32, u32, u64),
            (Vec<(Pose, SharedShape)>, Vec<String>),
        > = BTreeMap::new();
        for body in &plant.bodies {
            let mut pose = native_source_pose(body.translation_world_m, body.rotation_world_wxyz)?;
            pose.translation += lift;
            poses.insert(body.name.clone(), pose);
        }
        // Validate hull conversion before changing native state. Individual hulls
        // use the declared exterior role abstraction; its filled cavities and filters
        // are separate from manufacturing collision qualification.
        for collider in &plant.colliders {
            let leaf = native_collider_leaf(collider)?;
            // Pack unchanged hulls sharing a body and physical parameters into
            // one compound; keep each original hull and its source identity.
            let group = shape_groups
                .entry((
                    collider.body.clone(),
                    collider.contype,
                    collider.conaffinity,
                    collider.friction.to_bits(),
                ))
                .or_default();
            group.0.push(leaf);
            group.1.push(collider.name.clone());
        }
        let mut body_handles = HashMap::new();
        for body in &plant.bodies {
            let handle = world.bodies.insert(
                RigidBodyBuilder::dynamic()
                    .pose(poses[&body.name])
                    .additional_mass_properties(native_mass_properties(body)?)
                    .linear_damping(0.0)
                    .angular_damping(0.0)
                    .can_sleep(false)
                    .additional_solver_iterations(0),
            );
            body_handles.insert(body.name.clone(), handle);
        }
        let mut collider_source_groups = Vec::new();
        for ((owner, contype, affinity, friction), (children, source_names)) in shape_groups {
            let shape = ColliderBuilder::compound(children)
                .density(0.0)
                .friction(f64::from_bits(friction) as f32)
                .restitution(0.0)
                .collision_groups(groups(contype, affinity))
                .active_hooks(
                    ActiveHooks::FILTER_CONTACT_PAIRS | ActiveHooks::MODIFY_SOLVER_CONTACTS,
                );
            world
                .colliders
                .insert_with_parent(shape, body_handles[&owner], &mut world.bodies);
            collider_source_groups.push(source_names);
        }
        let mut body_measurements = Vec::new();
        for body in &plant.bodies {
            let native = &mut world.bodies[body_handles[&body.name]];
            native.recompute_mass_properties_from_colliders(&world.colliders);
            let properties = &native.mass_properties().local_mprops;
            let expected = engine_inertia(body.inertia_at_com_body_kg_m2);
            let observed = properties.reconstruct_inertia_matrix();
            let expected_elements = expected.to_cols_array();
            let observed_elements = observed.to_cols_array();
            let relative = (observed_elements
                .iter()
                .zip(expected_elements)
                .map(|(a, b)| (*a as f64 - b as f64).powi(2))
                .sum::<f64>()
                / expected_elements
                    .iter()
                    .map(|v| (*v as f64).powi(2))
                    .sum::<f64>())
            .sqrt();
            body_measurements.push(GooseBodyMeasurement {
                name: body.name.clone(),
                mass_kg: properties.mass(),
                mass_error_kg: (properties.mass() as f64 - body.mass_kg).abs(),
                com_error_m: (properties.local_com - engine_vector(body.com_local_m)?)
                    .abs()
                    .max_element() as f64,
                full_inertia_relative_error: relative,
            });
            if relative > 2e-5 || properties.inv_principal_inertia.min_element() <= 0.0 {
                return Err(invalid(format!(
                    "Goose backend changed full inertia: {} error={relative}",
                    body.name
                )));
            }
        }
        let mut mappings = Vec::new();
        for joint in &plant.joints {
            let parent_pose = poses[&joint.parent];
            let child_pose = poses[&joint.child];
            let axis = engine_vector(joint.axis_world)?;
            let world_frame = Pose::from_parts(
                engine_vector(joint.origin_world_m)? + lift,
                Rotation::from_rotation_arc(Vector::X, axis),
            );
            let (mask, coordinate, axis_kind) = if joint.kind == "slide" {
                (JointAxesMask::LOCKED_PRISMATIC_AXES, 0, JointAxis::LinX)
            } else {
                (JointAxesMask::LOCKED_REVOLUTE_AXES, 3, JointAxis::AngX)
            };
            let description = GenericJointBuilder::new(mask)
                .local_frame1(parent_pose.inverse() * world_frame)
                .local_frame2(child_pose.inverse() * world_frame)
                .limits(axis_kind, joint.range.map(|value| value as f32))
                .contacts_enabled(false);
            let parent = body_handles[&joint.parent];
            let child = body_handles[&joint.child];
            let handle = world
                .multibody_joints
                .insert(parent, child, description, true)
                .ok_or_else(|| invalid("Goose articulation is not a native tree"))?;
            mappings.push(JointMapping {
                handle,
                parent,
                child,
                coordinate,
                axis_parent: parent_pose.rotation.inverse() * axis,
                active_axis: joint.active_axis,
                feedback_axis: joint.feedback_axis,
            });
        }
        let first = mappings
            .first()
            .ok_or_else(|| invalid("Goose articulation absent"))?
            .handle;
        let (multibody, _) = world
            .multibody_joints
            .get_mut(first)
            .ok_or_else(|| invalid("Goose multibody absent"))?;
        multibody.set_self_contacts_enabled(true);
        multibody.forward_kinematics(&world.bodies, true);
        multibody.damping_mut().fill(0.0);
        multibody.armature_mut().fill(0.0);
        multibody.frictions_mut().fill(0.0);
        if multibody.ndofs() != plant.joints.len() + 6 {
            return Err(invalid("Goose free-root native DoF mismatch"));
        }
        let mut passive_spring_count = 0;
        for (mapping, joint) in mappings.iter().zip(&plant.joints) {
            let link_id = multibody
                .links()
                .find(|link| link.rigid_body_handle() == mapping.child)
                .ok_or_else(|| invalid("Goose native link absent"))?
                .link_id();
            let slot = multibody.link(link_id).unwrap().assembly_id();
            if multibody.link(link_id).unwrap().joint.ndofs() != 1 {
                return Err(invalid("Goose joint is not one scalar coordinate"));
            }
            if plant.numerical_experiment.is_some()
                && !multibody
                    .link_mut(link_id)
                    .unwrap()
                    .joint
                    .set_predictive_limits_enabled(true)
            {
                return Err(invalid(
                    "Goose experimental scalar predictive stop rejected",
                ));
            }
            multibody.damping_mut()[slot] = joint.damping as f32;
            multibody.armature_mut()[slot] = joint.armature as f32;
            multibody.frictions_mut()[slot] = joint.frictionloss as f32;
            if joint.stiffness_n_m > 0.0 {
                multibody.link_mut(link_id).unwrap().joint.set_spring(
                    mapping.coordinate,
                    joint.stiffness_n_m as f32,
                    0.0,
                );
                passive_spring_count += 1;
            }
        }
        let coupler = body_handles[&plant.jaw_loop.coupler_body];
        let jaw = body_handles[&plant.jaw_loop.jaw_body];
        let axis = engine_vector(plant.jaw_loop.rotation_axis_world)?;
        let pin = engine_vector(plant.jaw_loop.output_pin_world_m)? + lift;
        let pin_rotation = if plant.numerical_experiment.is_some() {
            let coupler_hinge = plant
                .joints
                .iter()
                .find(|joint| joint.child == plant.jaw_loop.coupler_body)
                .ok_or_else(|| invalid("Goose coupler hinge absent"))?;
            let coupler_origin = engine_vector(coupler_hinge.origin_world_m)? + lift;
            let direction = pin - coupler_origin;
            if direction.length_squared() <= 1e-12 {
                return Err(invalid("Goose coupler pin basis is degenerate"));
            }
            let x = direction.normalize();
            if x.dot(axis).abs() > 1e-5 {
                return Err(invalid("Goose coupler pin basis is not planar"));
            }
            Rotation::from_mat3(&Matrix::from_cols(x, axis.cross(x), axis)).normalize()
        } else {
            Rotation::from_rotation_arc(Vector::Z, axis)
        };
        let frame = Pose::from_parts(pin, pin_rotation);
        let frame1 = poses[&plant.jaw_loop.coupler_body].inverse() * frame;
        let frame2 = poses[&plant.jaw_loop.jaw_body].inverse() * frame;
        let loop_joint = GenericJointBuilder::new(JointAxesMask::LIN_X | JointAxesMask::LIN_Y)
            .local_frame1(frame1)
            .local_frame2(frame2)
            .contacts_enabled(false);
        let jaw_loop_handle = world.impulse_joints.insert(coupler, jaw, loop_joint, true);
        let mut excluded = HashSet::new();
        for pair in &plant.exclusions {
            excluded.insert(ordered_pair(body_handles[&pair[0]], body_handles[&pair[1]]));
        }
        Ok(Self {
            body_handles: body_handles.clone(),
            body_measurements,
            jaw_loop_handle,
            passive_spring_count,
            collider_count: collider_source_groups.len(),
            source_geometry_count: plant.colliders.len(),
            collider_source_groups,
            joints: mappings,
            hooks: GooseCollisionHooks {
                excluded,
                ground,
                feet: [
                    body_handles["right_ankle_roll"],
                    body_handles["left_ankle_roll"],
                ]
                .into_iter()
                .collect(),
            },
            pin_local_coupler: frame1.translation,
            pin_local_jaw: frame2.translation,
            coupler,
            jaw,
        })
    }

    /// Apply actual motor efforts as equal/opposite torques, then integrate once.
    pub fn step(
        &self,
        simulation: &mut SimulationWorld,
        torque_nm: [f64; 18],
    ) -> Result<(), SimulationError> {
        let mut torques = Vec::with_capacity(36);
        for mapping in &self.joints {
            if let Some(axis) = mapping.active_axis {
                let parent = simulation
                    .world
                    .bodies
                    .get(mapping.parent)
                    .ok_or(SimulationError::UnknownBody(mapping.parent))?;
                let torque = parent.rotation() * mapping.axis_parent * (torque_nm[axis] as f32);
                if !torque.is_finite() {
                    return Err(SimulationError::NonFiniteTorque);
                }
                torques.extend(BodyTorque::joint_pair(
                    mapping.parent,
                    mapping.child,
                    torque.to_array(),
                ));
            }
        }
        let world = &mut simulation.world;
        if world.integration_parameters.dt != 0.02
            || world.integration_parameters.num_solver_iterations != 1
            || world.integration_parameters.max_ccd_substeps > 1
        {
            return Err(SimulationError::NonFiniteTorque);
        }
        for (_, body) in world.bodies.iter_mut() {
            body.reset_torques(true);
        }
        for t in torques {
            world.bodies[t.body].add_torque(Vector::from_array(t.world_torque), true);
        }
        world.step_with_events(&self.hooks, &());
        if !world.quarantine().is_empty() {
            return Err(SimulationError::QuarantinedState);
        }
        for (h, b) in world.bodies.iter() {
            if !b.position().is_finite() || !b.linvel().is_finite() || !b.angvel().is_finite() {
                return Err(SimulationError::NonFiniteState(h));
            }
        }
        Ok(())
    }

    /// Read native joint feedback and IMU/root fields in the original SI basis.
    pub fn state(&self, simulation: &SimulationWorld) -> Result<GooseNativeState, RobotError> {
        let mut q = [0.0; 18];
        let mut qd = [0.0; 18];
        for mapping in &self.joints {
            if let Some(axis) = mapping.feedback_axis {
                let (multibody, link_id) = simulation
                    .world
                    .multibody_joints
                    .get(mapping.handle)
                    .ok_or_else(|| invalid("Stale Goose joint handle"))?;
                let link = multibody
                    .link(link_id)
                    .ok_or_else(|| invalid("Goose joint link absent"))?;
                q[axis] = link.joint.coords()[mapping.coordinate] as f64;
                qd[axis] = multibody.generalized_velocity()[link.assembly_id()] as f64;
            }
        }
        let torso = &simulation.world.bodies[self.body_handles["torso"]];
        let to_source = |value: Vector| engine_to_source_vector(value.to_array()).map(f64::from);
        let inverse = torso.rotation().inverse();
        let rotation = engine_to_source_rotation(torso.rotation().to_array())?.map(f64::from);
        Ok(GooseNativeState {
            gyro_body_rad_s: to_source(inverse * torso.angvel()),
            projected_gravity: to_source(inverse * Vector::NEG_Y),
            joint_position_rad: q,
            joint_velocity_rad_s: qd,
            root_position_world_m: to_source(torso.translation()),
            root_rotation_world_wxyz: rotation,
        })
    }

    /// Geometric loop error comes from the two actual native link transforms.
    pub fn jaw_pin_error_m(&self, simulation: &SimulationWorld) -> f32 {
        let coupler = simulation.world.bodies[self.coupler].position() * self.pin_local_coupler;
        let jaw = simulation.world.bodies[self.jaw].position() * self.pin_local_jaw;
        (coupler - jaw).length()
    }
}

fn invalid(message: impl Into<String>) -> RobotError {
    RobotError::Contract(message.into())
}
fn ordered_pair(first: RigidBodyHandle, second: RigidBodyHandle) -> [(u32, u32); 2] {
    let mut pair = [first.into_raw_parts(), second.into_raw_parts()];
    pair.sort();
    pair
}
fn groups(contype: u32, affinity: u32) -> InteractionGroups {
    InteractionGroups::new(
        Group::from_bits_retain(contype),
        Group::from_bits_retain(affinity),
        InteractionTestMode::Or,
    )
}
fn engine_vector(source: [f64; 3]) -> Result<Vector, RobotError> {
    let values = source.map(|value| value as f32);
    if values.iter().any(|value| !value.is_finite()) {
        return Err(invalid("Goose scalar cannot cross f32 boundary"));
    }
    Ok(Vector::from_array(source_to_engine_vector(values)))
}
/// Convert the same source pose for native body placement and collider inspection.
/// The caller owns any initial world lift; this conversion never adds one.
pub fn native_source_pose(position: [f64; 3], rotation: [f64; 4]) -> Result<Pose, RobotError> {
    let quaternion = source_to_engine_rotation(rotation.map(|value| value as f32))?;
    Ok(Pose::from_parts(
        engine_vector(position)?,
        Rotation::from_xyzw(quaternion[0], quaternion[1], quaternion[2], quaternion[3]),
    ))
}

/// Build one unchanged source collider, shared by the articulation and zero-step tools.
/// This does not construct a robot or bypass its condensed-contact guard.
pub fn native_collider_leaf(collider: &GooseCollider) -> Result<(Pose, SharedShape), RobotError> {
    let shape = match collider.kind.as_str() {
        "box" => {
            let source = collider
                .half_extents_m
                .ok_or_else(|| invalid("Goose box extents absent"))?;
            if source
                .iter()
                .any(|extent| !extent.is_finite() || *extent <= 0.0)
            {
                return Err(invalid("Invalid Goose box extent"));
            }
            let extent = engine_vector(source)?.abs();
            ColliderBuilder::cuboid(extent.x, extent.y, extent.z).shape
        }
        "convex_mesh" => {
            let source = collider
                .vertices_local_m
                .as_ref()
                .ok_or_else(|| invalid("Goose convex vertices absent"))?;
            if source.len() < 4 {
                return Err(invalid("Goose convex shape has too few vertices"));
            }
            let vertices = source
                .iter()
                .map(|value| engine_vector(*value))
                .collect::<Result<Vec<_>, _>>()?;
            let shape = ColliderBuilder::convex_hull(&vertices)
                .ok_or_else(|| invalid(format!("Goose hull collapsed: {}", collider.name)))?
                .shape;
            // Parry can construct a two-sided flat polygon. MuJoCo rejects that
            // input; accepting it here would silently cross the native boundary.
            let volume = shape.mass_properties(1.0).mass();
            if !volume.is_finite() || volume <= 0.0 {
                return Err(invalid(format!(
                    "Goose convex hull has no positive native volume: {}",
                    collider.name
                )));
            }
            shape
        }
        _ => return Err(invalid("Unsupported Goose geometry")),
    };
    Ok((
        native_source_pose(collider.local_position_m, collider.local_rotation_wxyz)?,
        shape,
    ))
}
fn engine_inertia(source: [[f64; 3]; 3]) -> Matrix {
    let index = [0, 2, 1];
    let sign = [1.0, 1.0, -1.0];
    Matrix::from_cols_array(&std::array::from_fn(|slot| {
        let row = slot % 3;
        let column = slot / 3;
        (sign[row] * sign[column] * source[index[row]][index[column]]) as f32
    }))
}
/// Convert the physical SI mass and complete body-frame tensor to the native basis.
/// Numerical integration terms must not be added to this physical mass ledger.
pub fn native_mass_properties(body: &GooseBody) -> Result<MassProperties, RobotError> {
    let tensor = body.inertia_at_com_body_kg_m2;
    let index = [0, 2, 1];
    let sign = [1.0, 1.0, -1.0];
    let matrix = na::Matrix3::<f64>::from_fn(|row, column| {
        sign[row] * sign[column] * tensor[index[row]][index[column]]
    });
    let scale = matrix
        .iter()
        .map(|value| value.abs())
        .fold(0.0_f64, f64::max);
    let eigen = (matrix / scale).symmetric_eigen();
    let diagonal = eigen.eigenvalues * scale;
    if diagonal
        .iter()
        .any(|value| !value.is_finite() || *value <= 0.0)
    {
        return Err(invalid("Goose inertia eigenvalue is not positive"));
    }
    let mut vectors = eigen.eigenvectors;
    if vectors.determinant() < 0.0 {
        vectors.set_column(0, &(-vectors.column(0)));
    }
    let frame = Matrix::from_cols_array(&std::array::from_fn(|slot| {
        vectors[(slot % 3, slot / 3)] as f32
    }));
    Ok(MassProperties::with_principal_inertia_frame(
        engine_vector(body.com_local_m)?,
        body.mass_kg as f32,
        Vector::new(diagonal[0] as f32, diagonal[1] as f32, diagonal[2] as f32),
        Rotation::from_mat3(&frame).normalize(),
    ))
}
