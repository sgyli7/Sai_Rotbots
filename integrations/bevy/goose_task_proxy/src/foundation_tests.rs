use rapier3d::{
    geometry::ExperimentalNormalSpring,
    math::{Pose, Vector},
    pipeline::ContactModificationContext,
    prelude::*,
};
struct Foundation;
impl PhysicsHooks for Foundation {
    fn modify_solver_contacts(&self, c: &mut ContactModificationContext) {
        if !c.solver_contacts.is_empty() {
            let n = c.solver_contacts.len() as f32;
            *c.experimental_normal_spring = Some(ExperimentalNormalSpring {
                stiffness_n_m: 140142.1824 / n,
                damping_n_s_m: 12.0 / n,
            });
        }
    }
}
fn fixture(force: f32) -> (f32, f32) {
    let mut w = PhysicsWorld::new();
    w.integration_parameters.dt = 0.02;
    w.integration_parameters.num_solver_iterations = 1;
    w.integration_parameters.num_internal_pgs_iterations = 32;
    w.integration_parameters.max_ccd_substeps = 1;
    w.integration_parameters.normalized_prediction_distance = 0.01;
    w.integration_parameters.warmstart_coefficient = 0.0;
    let ground = w.bodies.insert(RigidBodyBuilder::fixed());
    w.colliders.insert_with_parent(
        ColliderBuilder::halfspace(rapier3d::na::Unit::new_unchecked(Vector::Y)).friction(0.65),
        ground,
        &mut w.bodies,
    );
    let foot = w.bodies.insert(
        RigidBodyBuilder::dynamic()
            .translation(Vector::new(0.0, 0.012, 0.0))
            .additional_mass(5.215)
            .can_sleep(false),
    );
    w.colliders.insert_with_parent(
        ColliderBuilder::cuboid(0.07, 0.01, 0.04)
            .density(0.0)
            .friction(0.65)
            .active_hooks(ActiveHooks::MODIFY_SOLVER_CONTACTS),
        foot,
        &mut w.bodies,
    );
    // Native free multibody root, so the generic articulated contact solver is used.
    let dummy = w.bodies.insert(
        RigidBodyBuilder::dynamic()
            .translation(Vector::new(0.0, 0.012, 0.0))
            .additional_mass(0.000001)
            .can_sleep(false),
    );
    w.multibody_joints
        .insert(
            foot,
            dummy,
            GenericJointBuilder::new(JointAxesMask::LOCKED_FIXED_AXES)
                .local_frame1(Pose::IDENTITY)
                .local_frame2(Pose::IDENTITY),
            true,
        )
        .unwrap();
    for tick in 0..200 {
        w.bodies[foot].reset_forces(true);
        if tick >= 100 {
            w.bodies[foot].add_force(Vector::X * force, true);
        }
        w.step_with_events(&Foundation, &());
        assert!(w.quarantine().is_empty());
    }
    (
        0.01 - w.bodies[foot].translation().y,
        w.bodies[foot].linvel().x,
    )
}
#[test]
fn loaded_sole_matches_static_spring_law() {
    let (depth, speed) = fixture(0.0);
    let expected = 5.215 * 9.81 / 140142.1824;
    assert!(
        (depth - expected).abs() < 1e-5,
        "depth={depth},expected={expected}"
    );
    assert!(speed.abs() < 1e-4);
}
#[test]
fn coulomb_friction_holds_below_and_slips_above_limit() {
    let (_, slow) = fixture(10.0);
    let (_, fast) = fixture(50.0);
    assert!(slow.abs() < 0.01, "below-limit slip={slow}");
    assert!(fast > 1.0, "above-limit speed={fast}");
}
