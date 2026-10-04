extends Node3D
## Deliberately impossible collider placements test filtering only. There are no
## robot inertias, articulation rollouts, learned actions or manufacturing claims.
const Policy = preload("res://collision_policy.gd")
const ContactBody = preload("res://contact_body.gd")
var input: Dictionary
var shapes: Dictionary = {}
var rows: Array = []
var failures: Array = []
var output_path := ""

func fail(message: String) -> void:
	push_error(message)
	failures.append(message)

func body(label: String, shape: Shape3D, point: Vector3) -> RigidBody3D:
	var b := ContactBody.new()
	b.name = label
	b.mass = 1.0
	b.gravity_scale = 0.0
	b.can_sleep = false
	b.linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	b.angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	b.linear_damp = 0.0
	b.angular_damp = 0.0
	b.contact_monitor = true
	b.max_contacts_reported = 64
	b.collision_layer = 1
	b.collision_mask = 1
	var cs := CollisionShape3D.new()
	cs.shape = shape
	b.add_child(cs)
	b.position = point
	add_child(b)
	return b

func instance(label: String) -> Dictionary:
	var bodies: Dictionary = {}
	var i := 0
	for role in shapes:
		bodies[role] = body(label + "_" + role, shapes[role], Vector3(20 + i*2, 20, 0))
		i += 1
	# Exercise restoration from a stale forbidden exclusion before every fixture.
	bodies.torso_envelope.add_collision_exception_with(bodies.head_upper_bill_envelope)
	bodies.head_upper_bill_envelope.add_collision_exception_with(bodies.torso_envelope)
	var error: String = Policy.apply(input.policy, input.plant, bodies)
	if not error.is_empty(): fail(error)
	return bodies

func fixture(first: String, second: String, scope: String, enabled: bool, control: bool = false) -> Dictionary:
	var robot := instance("robot")
	var peer: Dictionary = {}
	var a: RigidBody3D = robot[first]
	var b: RigidBody3D
	a.position = Vector3.ZERO
	if scope == "same_instance":
		b = robot[second]
	elif scope == "other_robot":
		peer = instance("peer")
		b = peer[second]
	else:
		var shape: Shape3D
		if scope == "ground":
			var floor_shape := BoxShape3D.new()
			floor_shape.size = Vector3(4, .02, 4)
			shape = floor_shape
		else:
			var sphere := SphereShape3D.new()
			sphere.radius = .005
			shape = sphere
		b = body(scope, shape, Vector3.ZERO)
		# Use an actual static environment body for both external-contact scopes.
		PhysicsServer3D.body_set_mode(b.get_rid(), PhysicsServer3D.BODY_MODE_STATIC)
	b.position = Vector3(.003, -.002, .001)
	if control:
		a.remove_collision_exception_with(b)
		b.remove_collision_exception_with(a)
	var shape_a: Shape3D = a.get_child(0).shape
	var shape_b: Shape3D = b.get_child(0).shape
	# Shape3D has no pair query. Probe the same cooked shape against a separate
	# unfiltered static copy in the native space, away from the measured bodies.
	var witness_body := StaticBody3D.new()
	var witness_shape := CollisionShape3D.new()
	witness_shape.shape = shape_b
	witness_body.add_child(witness_shape)
	witness_body.position = Vector3(.003, 9.998, .001)
	add_child(witness_body)
	await get_tree().physics_frame
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = shape_a
	query.transform = Transform3D(Basis.IDENTITY, Vector3(0, 10, 0))
	query.collision_mask = 1
	var excluded: Array[RID] = []
	for child in get_children():
		if child is PhysicsBody3D and child != witness_body: excluded.append(child.get_rid())
	query.exclude = excluded
	var witness: Array[Vector3] = get_world_3d().direct_space_state.collide_shape(query, 32)
	if witness.size() < 2: fail("No raw penetration witness: " + first + "/" + second + "/" + scope)
	var raw_penetration := 0.0
	for i in range(0, witness.size(), 2):
		raw_penetration = maxf(raw_penetration, witness[i].distance_to(witness[i+1]))
	if raw_penetration < 0.00001: fail("Witness has no finite penetration depth")
	witness_body.queue_free()
	# Give a small approach velocity; read solver-produced contact callbacks.
	a.linear_velocity = Vector3(.01, 0, 0)
	for i in range(6): await get_tree().physics_frame
	var contacts := int(a.peak_contacts.get(b.get_rid(), 0))
	var actual := contacts > 0
	if actual != enabled: fail("Native contact differs: " + first + "/" + second + "/" + scope)
	var result := {"scope": scope, "first": first, "second": second,
		"unfiltered_control": control, "expected_collision_enabled": enabled,
		"raw_contact_points": witness.size()/2, "raw_penetration_m": raw_penetration,
		"native_contact_samples": contacts, "native_peak_reported_impulse_Ns": a.peak_impulse,
		"collision_enabled": actual}
	for n in robot.values(): n.queue_free()
	for n in peer.values(): n.queue_free()
	if scope in ["ground", "object"]: b.queue_free()
	await get_tree().process_frame
	return result

func rejection_checks() -> Dictionary:
	var result: Dictionary = {}
	for roles in [["head_upper_bill_envelope", "torso_envelope"], ["left_flexible_sole", "right_flexible_sole"]]:
		var altered: Dictionary = input.policy.duplicate(true)
		for row in altered.pairs:
			if Policy.pair_key(row.first, row.second) == Policy.pair_key(roles[0], roles[1]): row.collision_enabled = false
		result[Policy.pair_key(roles[0], roles[1])] = not Policy.validate(altered, input.plant).is_empty()
	var incomplete: Dictionary = input.policy.duplicate(true)
	incomplete.pairs.pop_back()
	result.incomplete_pair_table = not Policy.validate(incomplete, input.plant).is_empty()
	var broken_chain: Dictionary = input.policy.duplicate(true)
	for row in broken_chain.pairs:
		if not row.collision_enabled:
			row.connected_body_chain = []
			break
	result.missing_connection_witness = not Policy.validate(broken_chain, input.plant).is_empty()
	var robot := instance("rejection_robot")
	var aliased: Dictionary = robot.duplicate()
	aliased[input.plant.colliders[1].name] = aliased[input.plant.colliders[0].name]
	result.aliased_instance_handles = not Policy.apply(input.policy, input.plant, aliased).is_empty()
	# Remove every allowed exclusion and add a stale forbidden one, then reapply
	# to the same live instance and verify exact recovery in both directions.
	for row in input.policy.pairs:
		if not row.collision_enabled:
			robot[row.first].remove_collision_exception_with(robot[row.second])
			robot[row.second].remove_collision_exception_with(robot[row.first])
	robot.torso_envelope.add_collision_exception_with(robot.head_upper_bill_envelope)
	robot.head_upper_bill_envelope.add_collision_exception_with(robot.torso_envelope)
	result.live_instance_reapplication = Policy.apply(input.policy, input.plant, robot).is_empty()
	var joint := PhysicsServer3D.joint_create()
	PhysicsServer3D.joint_make_pin(joint, robot.upper_neck_envelope.get_rid(), Vector3.ZERO,
		robot.head_upper_bill_envelope.get_rid(), Vector3.ZERO)
	PhysicsServer3D.joint_disable_collisions_between_bodies(joint, true)
	Policy.configure_joint(joint)
	result.joint_default_reset = (not PhysicsServer3D.joint_is_disabled_collisions_between_bodies(joint)
		and Policy.verify(input.policy, robot).is_empty())
	PhysicsServer3D.free_rid(joint)
	for n in robot.values(): n.queue_free()
	for key in result:
		if not result[key]: fail("Rejection/lifecycle check failed: " + key)
	return result

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		fail("Expected input JSON and output JSON paths")
		get_tree().quit(2)
		return
	output_path = args[1]
	input = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var error: String = Policy.validate(input.policy, input.plant)
	if not error.is_empty():
		fail(error)
		get_tree().quit(2)
		return
	for role in input.shapes:
		var hull := ConvexPolygonShape3D.new()
		var points := PackedVector3Array()
		for v in input.shapes[role]: points.append(Vector3(v[0], v[1], v[2]))
		hull.points = points
		hull.margin = .001
		shapes[role] = hull
	await get_tree().physics_frame
	var rejections := rejection_checks()
	await get_tree().process_frame
	for row in input.policy.pairs:
		rows.append(await fixture(row.first, row.second, "same_instance", row.collision_enabled))
		rows.append(await fixture(row.first, row.second, "same_instance", true, true))
	for role in shapes:
		for scope in ["ground", "object", "other_robot"]:
			rows.append(await fixture(role, role if scope == "other_robot" else scope, scope, true))
	for row in input.policy.pairs:
		if not row.collision_enabled:
			rows.append(await fixture(row.first, row.second, "other_robot", true))
	var report := {"schema": "goose_godot_collision_filter_probe_v1", "candidate_id": input.policy.candidate_id,
		"godot_version": Engine.get_version_info().string,
		"physics_engine": ProjectSettings.get_setting("physics/3d/physics_engine"),
		"physics_dt_s": 1.0/float(ProjectSettings.get_setting("physics/common/physics_ticks_per_second")),
		"rows": rows, "rejection_checks": rejections, "failures": failures,
		"passed": failures.is_empty(), "full_task_success_claim": false,
		"scope": "Independent native cooked-shape/filter fixtures; 1 kg diagnostic bodies, no full robot rollout or hardware changes"}
	var file := FileAccess.open(output_path, FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print("GOOSE_COLLISION_FILTER_RESULT " + JSON.stringify({"passed": failures.is_empty(), "fixtures": rows.size(), "engine": report.physics_engine}))
	get_tree().quit(0 if failures.is_empty() else 2)
