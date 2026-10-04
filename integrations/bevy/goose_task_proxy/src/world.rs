use rapier3d::prelude::*;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PhysicsClockProfile {
    Goose50,
}
pub struct SimulationWorld {
    pub world: PhysicsWorld,
}
impl SimulationWorld {
    pub fn new_with_profile(_: PhysicsClockProfile) -> Self {
        let mut world = PhysicsWorld::new();
        world.integration_parameters.dt = 0.02;
        world.integration_parameters.num_solver_iterations = 1;
        world.integration_parameters.max_ccd_substeps = 1;
        Self { world }
    }
    pub fn clock_profile(&self) -> PhysicsClockProfile {
        PhysicsClockProfile::Goose50
    }
}
pub struct BodyTorque {
    pub body: RigidBodyHandle,
    pub world_torque: [f32; 3],
}
impl BodyTorque {
    pub fn joint_pair(parent: RigidBodyHandle, child: RigidBodyHandle, t: [f32; 3]) -> [Self; 2] {
        [
            Self {
                body: parent,
                world_torque: t.map(|v| -v),
            },
            Self {
                body: child,
                world_torque: t,
            },
        ]
    }
}
#[derive(Debug, thiserror::Error)]
pub enum SimulationError {
    #[error("unknown body {0:?}")]
    UnknownBody(RigidBodyHandle),
    #[error("invalid torque or timestep")]
    NonFiniteTorque,
    #[error("quarantined state")]
    QuarantinedState,
    #[error("nonfinite state {0:?}")]
    NonFiniteState(RigidBodyHandle),
}
