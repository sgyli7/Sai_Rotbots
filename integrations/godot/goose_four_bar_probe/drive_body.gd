extends RigidBody3D
var probe: Node3D
var sim_t := 0.0
var next_trace := 0.0
var previous_q := 0.0
var first := true
func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	var q := state.transform.basis.get_euler().z
	var target: float = probe.reference_q()
	var torque: float = .012*(target-q)-.0003*state.angular_velocity.z + 0.025*probe.fx*sin(q)
	if first:
		probe.drive_trace.append({"actual_inverse_inertia_z":state.inverse_inertia_tensor.z.z,"inverse_mass":state.inverse_mass})
	previous_q = q
	first = false
	sim_t += state.step
	state.apply_torque(Vector3(0, 0, clampf(torque, -.05, .05)*probe.MASS_UNIT_SCALE))
