extends Node3D
## Fixed-base loop probe; artificial bodies/drive. No CAD or hardware validation.
const L := 0.025
const H := 0.014
const MASS_UNIT_SCALE := 100.0
var lower: RigidBody3D
var upper: RigidBody3D
var jaw: RigidBody3D
var ground: StaticBody3D
var joints: Array[RID] = []
var t := 0.0
var count := 0
var max_closure := 0.0
var max_tilt := 0.0
var max_path := 0.0
var max_tracking := 0.0
var q_min := INF
var q_max := -INF
var fx := 0.0
var samples := 0
var drive_trace: Array = []

func rod(label: String, m: float, p: Vector3, q: float, length: float, vertical: bool) -> RigidBody3D:
	var b := RigidBody3D.new()
	b.name = label
	if label == "lower_crank":
		b.set_script(load("res://drive_body.gd"))
		b.set("probe", self)
	b.mass = m*MASS_UNIT_SCALE
	var inertia_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://inertia.json"))[label]
	var iv: Array = inertia_data.godot_local_inertia
	b.inertia = Vector3(iv[0], iv[1], iv[2])*MASS_UNIT_SCALE
	b.gravity_scale = 0.0
	b.can_sleep = false
	b.linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	b.angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	b.linear_damp = 0.0
	b.angular_damp = 0.0
	b.collision_layer = 1
	b.collision_mask = 0
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.001
	cap.height = length + 0.002
	cs.shape = cap
	if not vertical: cs.rotation.z = PI / 2.0
	b.add_child(cs)
	b.position = p
	b.rotation.z = q
	add_child(b)
	return b

func hinge(a: PhysicsBody3D, b: PhysicsBody3D, point: Vector3) -> void:
	var rid := PhysicsServer3D.joint_create()
	var fa := a.global_transform.affine_inverse() * Transform3D(Basis.IDENTITY, point)
	var fb := b.global_transform.affine_inverse() * Transform3D(Basis.IDENTITY, point)
	PhysicsServer3D.joint_make_hinge(rid, a.get_rid(), fa, b.get_rid(), fb)
	PhysicsServer3D.hinge_joint_set_flag(rid, PhysicsServer3D.HINGE_JOINT_FLAG_USE_LIMIT, false)
	joints.append(rid)

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size(): fx = float(args[0])
	var q := deg_to_rad(40.0)
	var a := Vector3.ZERO
	var d := Vector3(0, H, 0)
	var b := Vector3(L*cos(q), L*sin(q), 0)
	var c := b + d
	ground = StaticBody3D.new()
	ground.name = "fixed_frame"
	ground.collision_layer = 0
	ground.collision_mask = 0
	add_child(ground)
	lower = rod("lower_crank", .005, b*.5, q, L, false)
	upper = rod("upper_crank", .005, d+b*.5, q, L, false)
	jaw = rod("jaw", .020, (b+c)*.5, 0.0, H, true)
	hinge(ground, lower, a)
	hinge(lower, jaw, b)
	hinge(ground, upper, d)
	hinge(jaw, upper, c)

func reference_q() -> float:
	var closed := deg_to_rad(40.0)
	var opened := deg_to_rad(-33.863234334283845)
	return closed+(opened-closed)*(.5-.5*cos(TAU*t/4.0))

func _physics_process(delta: float) -> void:
	var target := reference_q()
	var q := lower.rotation.z
	jaw.apply_central_force(Vector3(fx*MASS_UNIT_SCALE, 0, 0))
	if t >= .5:
		var cb := jaw.global_transform * Vector3(0, H*.5, 0)
		var cc := upper.global_transform * Vector3(L*.5, 0, 0)
		var expected := Vector3(L*cos(q), L*sin(q)+H, 0)
		max_closure = maxf(max_closure, cb.distance_to(cc))
		max_path = maxf(max_path, cb.distance_to(expected))
		max_tilt = maxf(max_tilt, absf(jaw.rotation.z))
		max_tracking = maxf(max_tracking, absf(q-target))
		q_min = minf(q_min, q)
		q_max = maxf(q_max, q)
		samples += 1
	t += delta
	count += 1
	if t >= 6.0:
		var result := {"scope":"Isolated fixed-base four-hinge ideal loop; artificial masses and PD/feedforward drive; no robot/CAD/real servo/grasp test", "godot_version":Engine.get_version_info().string, "physics_engine":ProjectSettings.get_setting("physics/3d/physics_engine"), "dt_s":delta, "hinge_constraints":joints.size(), "artificial_applied_jaw_com_force_N":[fx,0,0], "max_loop_residual_mm":1000*max_closure, "max_jaw_tilt_deg":rad_to_deg(max_tilt), "max_ideal_path_residual_mm":1000*max_path, "max_target_tracking_error_deg":rad_to_deg(max_tracking), "actual_crank_range_deg":[rad_to_deg(q_min),rad_to_deg(q_max)], "samples":samples, "drive_trace":drive_trace, "gravity":0, "geometric_contacts_disabled":true, "real_motor_model":false, "mass_unit_scale":MASS_UNIT_SCALE}
		var file := FileAccess.open("res://godot_result_%s.json" % str(fx), FileAccess.WRITE)
		file.store_string(JSON.stringify(result, "\t")+"\n")
		print(JSON.stringify(result))
		for rid in joints: PhysicsServer3D.free_rid(rid)
		get_tree().quit(0)
