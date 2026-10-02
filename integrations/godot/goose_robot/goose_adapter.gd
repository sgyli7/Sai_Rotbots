extends Node3D
## This is one consumer of rigid_transfer.json; the source data remain SI.
## Bodies use principal COM frames, including products of inertia from CAD.
const MASS_SCALE := 100.0
const C := Basis(Vector3(1,0,0), Vector3(0,0,-1), Vector3(0,1,0))
var transfer: Dictionary
var bodies: Dictionary = {}
var descriptions: Dictionary = {}
var model_frames: Dictionary = {}
var initial_model_rotations: Dictionary = {}
var constraints: Array[RID] = []
var joint_records: Array[Dictionary] = []
var t := 0.0
var duration := 4.0
var root_start := Vector3.ZERO
var max_tilt := 0.0
var max_joint_error := 0.0
var max_loop_residual := 0.0
var saturation_count := 0
var sample_count := 0
var trace: Array = []
var udp_enabled := false
var udp := PacketPeerUDP.new()
var sensor_sequence := 0
var external_torques: Dictionary = {}
var action_expiry_s := -1.0
var filtered_speeds: Dictionary = {}
var stance_targets: Dictionary = {}
var torque_sample_steps := 5

func vector(a: Array) -> Vector3:
	return Vector3(float(a[0]),float(a[1]),float(a[2]))

func quaternion(a: Array) -> Basis:
	return Basis(Quaternion(float(a[1]),float(a[2]),float(a[3]),float(a[0])))

func rotation(a: Array) -> Basis:
	return Basis(Vector3(a[0][0],a[1][0],a[2][0]),Vector3(a[0][1],a[1][1],a[2][1]),Vector3(a[0][2],a[1][2],a[2][2]))

func to_engine_basis(b: Basis) -> Basis:
	return C*b*C.transposed()

func model_transform(label: String) -> Transform3D:
	return bodies[label].global_transform*model_frames[label].affine_inverse()

func collision_shape(g: Dictionary) -> Shape3D:
	var size := vector(g.size_m)
	match String(g.type):
		"box":
			var s := BoxShape3D.new();s.size=Vector3(size.x,size.z,size.y)*2;return s
		"sphere":
			var s := SphereShape3D.new();s.radius=size.x;return s
		"capsule":
			var s := CapsuleShape3D.new();s.radius=size.x;s.height=2*(size.y+size.x);return s
		"cylinder":
			var s := CylinderShape3D.new();s.radius=size.x;s.height=2*size.y;return s
		"ellipsoid":
			var s := ConvexPolygonShape3D.new();var points := PackedVector3Array()
			for latitude in range(1,8):
				var theta := PI*latitude/8.0
				for longitude in range(16):
					var phi := TAU*longitude/16.0
					points.append(C*Vector3(size.x*sin(theta)*cos(phi),size.y*sin(theta)*sin(phi),size.z*cos(theta)))
			points.append(C*Vector3(0,0,size.z));points.append(C*Vector3(0,0,-size.z));s.points=points;return s
		"mesh":
			var s := ConvexPolygonShape3D.new();var points := PackedVector3Array()
			for point in g.vertices_local_m:points.append(C*vector(point))
			s.points=points;return s
		_:
			push_error("Unsupported collision geometry: "+String(g.type));get_tree().quit(2);return null

func attach_geometry(g: Dictionary) -> void:
	if String(g.body)=="world":return
	var b: RigidBody3D=bodies[g.body]
	var body_from_geom := Transform3D(to_engine_basis(quaternion(g.local_orientation_wxyz)),C*vector(g.local_position_m))
	var principal_from_geom: Transform3D=model_frames[g.body].affine_inverse()*body_from_geom
	if bool(g.contact):
		var cs := CollisionShape3D.new();cs.name=String(g.name)+"_collision";cs.shape=collision_shape(g)
		cs.transform=principal_from_geom;b.add_child(cs)
	if String(g.type)=="mesh" and float(g.rgba[3])>0:
		var mesh := ArrayMesh.new();var arrays := [];arrays.resize(Mesh.ARRAY_MAX)
		var vertices := PackedVector3Array();var indices := PackedInt32Array()
		for v in g.vertices_local_m:vertices.append(C*vector(v))
		# Both coordinate bases have positive determinant; winding is preserved.
		for face in g.triangles:
			for index in face:indices.append(int(index))
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_INDEX]=indices
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		var mi := MeshInstance3D.new();mi.name=String(g.name);mi.mesh=mesh;mi.transform=principal_from_geom
		var material := StandardMaterial3D.new();material.albedo_color=Color(g.rgba[0],g.rgba[1],g.rgba[2],g.rgba[3]);material.cull_mode=BaseMaterial3D.CULL_DISABLED
		mi.material_override=material;b.add_child(mi)

func axis_frame(axis: Vector3, point: Vector3, slider: bool) -> Transform3D:
	axis=axis.normalized()
	var helper := Vector3.UP if absf(axis.dot(Vector3.UP))<.8 else Vector3.RIGHT
	var x: Vector3;var y: Vector3;var z: Vector3
	if slider:
		x=axis;z=x.cross(helper).normalized();y=z.cross(x).normalized()
	else:
		z=axis;x=helper.cross(z).normalized();y=z.cross(x).normalized()
	return Transform3D(Basis(x,y,z),point)

func build_joint(j: Dictionary) -> void:
	if float(j.armature_kg_m2)!=0:
		push_error("Adapter requires explicit zero armature until reflected inertia is represented physically.");get_tree().quit(2);return
	var a: RigidBody3D=bodies[j.parent];var b: RigidBody3D=bodies[j.child]
	var slider := String(j.type)=="slide"
	var world_frame := axis_frame(C*vector(j.home_axis_world),C*vector(j.home_anchor_world_m),slider)
	var fa := a.global_transform.affine_inverse()*world_frame;var fb := b.global_transform.affine_inverse()*world_frame
	var rid := PhysicsServer3D.joint_create()
	if slider:
		PhysicsServer3D.joint_make_slider(rid,a.get_rid(),fa,b.get_rid(),fb)
		PhysicsServer3D.slider_joint_set_param(rid,PhysicsServer3D.SLIDER_JOINT_LINEAR_LIMIT_LOWER,float(j.range[0])-float(j.home))
		PhysicsServer3D.slider_joint_set_param(rid,PhysicsServer3D.SLIDER_JOINT_LINEAR_LIMIT_UPPER,float(j.range[1])-float(j.home))
		PhysicsServer3D.slider_joint_set_param(rid,PhysicsServer3D.SLIDER_JOINT_ANGULAR_LIMIT_LOWER,0)
		PhysicsServer3D.slider_joint_set_param(rid,PhysicsServer3D.SLIDER_JOINT_ANGULAR_LIMIT_UPPER,0)
	else:
		PhysicsServer3D.joint_make_hinge(rid,a.get_rid(),fa,b.get_rid(),fb)
		PhysicsServer3D.hinge_joint_set_flag(rid,PhysicsServer3D.HINGE_JOINT_FLAG_USE_LIMIT,bool(j.limited))
		# Godot 4.7.2 Jolt legacy hinge API uses the opposite angle convention.
		# Measured q and external equal/opposite torques still use right-handed SI.
		PhysicsServer3D.hinge_joint_set_param(rid,PhysicsServer3D.HINGE_JOINT_LIMIT_LOWER,float(j.home)-float(j.range[1]))
		PhysicsServer3D.hinge_joint_set_param(rid,PhysicsServer3D.HINGE_JOINT_LIMIT_UPPER,float(j.home)-float(j.range[0]))
	PhysicsServer3D.joint_disable_collisions_between_bodies(rid,true)
	a.add_collision_exception_with(b);b.add_collision_exception_with(a)
	constraints.append(rid)
	var record := j.duplicate(true)
	record.frame_a=fa;record.frame_b=fb;record.initial_relative=model_transform(j.parent).basis.inverse()*model_transform(j.child).basis
	record.axis_parent=model_transform(j.parent).basis.inverse()*(C*vector(j.home_axis_world))
	joint_records.append(record)

func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size():duration=float(arguments[0])
	udp_enabled=arguments.has("--udp")
	if udp_enabled:
		if udp.bind(19041,"127.0.0.1")!=OK:push_error("Cannot bind backend control socket");get_tree().quit(2);return
		udp.set_dest_address("127.0.0.1",19042)
	transfer=JSON.parse_string(FileAccess.get_file_as_string("res://rigid_transfer.json"))
	if transfer.get("schema","")!="sai_rigid_transfer_v1":push_error("Wrong transfer schema");get_tree().quit(2);return
	var ticks := float(ProjectSettings.get_setting("physics/common/physics_ticks_per_second"))
	var desired_steps := float(transfer.control.torque_update_dt_s)*ticks
	if absf(desired_steps-roundf(desired_steps))>.0001 or desired_steps<1:
		push_error("Torque cadence is not an integer number of backend physics steps");get_tree().quit(2);return
	torque_sample_steps=int(roundf(desired_steps))
	stance_targets=transfer.reference_poses.standing.active_joint_positions_rad
	for desc in transfer.bodies:
		var b := RigidBody3D.new();b.name=String(desc.name);b.mass=float(desc.mass_kg)*MASS_SCALE
		b.contact_monitor=true;b.max_contacts_reported=32
		# Each rigid body origin is the exported principal COM. Shape-derived AUTO
		# COM would silently move it and invalidate the shared SI mass model.
		b.center_of_mass_mode=RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
		b.center_of_mass=Vector3.ZERO
		# Basis conversion can negate a component; inertia magnitudes are
		# principal values. Never pass an intermediate negative value to Godot.
		b.inertia=(C*vector(desc.principal_inertia_kg_m2)).abs()*MASS_SCALE
		b.can_sleep=false;b.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE;b.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
		b.linear_damp=0;b.angular_damp=0;b.collision_layer=1;b.collision_mask=1
		var material := PhysicsMaterial.new();material.friction=.8;material.bounce=0;b.physics_material_override=material
		model_frames[desc.name]=Transform3D(to_engine_basis(quaternion(desc.principal_frame_local_wxyz)),C*vector(desc.com_local_m))
		b.transform=Transform3D(to_engine_basis(rotation(desc.home_principal_rotation_world)),C*vector(desc.home_com_world_m))
		add_child(b);bodies[desc.name]=b;descriptions[desc.name]=desc
		initial_model_rotations[desc.name]=model_transform(desc.name).basis
	for g in transfer.geometries:attach_geometry(g)
	var floor_body := StaticBody3D.new();floor_body.name="floor";var floor_shape := CollisionShape3D.new();var plane := BoxShape3D.new()
	plane.size=Vector3(6,.1,6);floor_shape.shape=plane;floor_shape.position.y=-.05;floor_body.add_child(floor_shape);add_child(floor_body)
	var floor_material := PhysicsMaterial.new();floor_material.friction=.8;floor_body.physics_material_override=floor_material
	for j in transfer.joints:build_joint(j)
	for exclusion in transfer.contact_exclusions:
		bodies[exclusion.body1].add_collision_exception_with(bodies[exclusion.body2]);bodies[exclusion.body2].add_collision_exception_with(bodies[exclusion.body1])
	# The convex-cluster approximation of the concave torso opening overlaps
	# the inboard hip-roll case in Jolt. Exact CAD and MuJoCo exclude contact
	# there; this is an adapter collision-shape exception, not a source-model edit.
	for side in ["left","right"]:
		var hip: RigidBody3D=bodies[side+"_hip_roll"]
		bodies.torso.add_collision_exception_with(hip);hip.add_collision_exception_with(bodies.torso)
	for loop in transfer.constraints:
		if String(loop.type)!="point_closure":push_error("Unsupported loop constraint");get_tree().quit(2);return
		var a: RigidBody3D=bodies[loop.body_a];var b: RigidBody3D=bodies[loop.body_b]
		var point := C*vector(loop.home_anchor_world_m);var rid := PhysicsServer3D.joint_create()
		PhysicsServer3D.joint_make_pin(rid,a.get_rid(),a.global_transform.affine_inverse()*point,b.get_rid(),b.global_transform.affine_inverse()*point)
		PhysicsServer3D.joint_disable_collisions_between_bodies(rid,true);constraints.append(rid)
	# Joint-local anchors above are built from the shared home configuration.
	# Move the entire valid kinematic assembly to the named neutral ground pose
	# before simulation, so every backend compares the same initial stance.
	for pose_body in transfer.reference_poses.standing.bodies:
		bodies[pose_body.name].global_transform=Transform3D(
			to_engine_basis(rotation(pose_body.principal_rotation_world)),
			C*vector(pose_body.com_world_m))
	root_start=model_transform("torso").origin
	var camera := Camera3D.new();camera.position=Vector3(.85,.55,.8);add_child(camera);camera.look_at(Vector3(.02,.30,0));camera.current=true
	var light := DirectionalLight3D.new();light.rotation=Vector3(-.8,-.6,0);add_child(light)

func smooth_speed(label: String, speed: float) -> float:
	# Jolt's instantaneous constraint velocities contain high-frequency solver
	# chatter. A short causal filter gives the SI encoder contract a motor-scale
	# velocity while retaining the same joint order and units for every backend.
	var value := lerpf(float(filtered_speeds.get(label, 0.0)), speed, .5)
	filtered_speeds[label] = value
	return value

func measured_joint(j: Dictionary) -> Array:
	var a: RigidBody3D=bodies[j.parent];var b: RigidBody3D=bodies[j.child]
	var ma := model_transform(j.parent);var mb := model_transform(j.child)
	var axis: Vector3=ma.basis*j.axis_parent
	if String(j.type)=="slide":
		var pa: Vector3=a.global_transform*j.frame_a.origin;var pb: Vector3=b.global_transform*j.frame_b.origin
		return [float(j.home)+(pb-pa).dot(axis),smooth_speed(j.name,(b.linear_velocity-a.linear_velocity).dot(axis)),axis]
	var relative: Basis=ma.basis.inverse()*mb.basis*j.initial_relative.inverse()
	var q := relative.get_rotation_quaternion();var qv := Vector3(q.x,q.y,q.z)
	var angle := wrapf(2*atan2(qv.dot(j.axis_parent),q.w),-PI,PI)
	return [float(j.home)+angle,smooth_speed(j.name,(b.angular_velocity-a.angular_velocity).dot(axis)),axis]

func exchange_control() -> bool:
	var states: Dictionary={}
	for j in joint_records:
		if bool(j.actuated):states[j.name]=measured_joint(j)
	var positions: Array=[];var velocities: Array=[]
	for label in transfer.control.encoder_joint_names:
		positions.append(states[label][0]);velocities.append(states[label][1])
	var root := model_transform("torso")
	var gyro: Vector3=C.transposed()*root.basis.transposed()*bodies.torso.angular_velocity
	var gravity: Vector3=C.transposed()*root.basis.transposed()*Vector3.DOWN
	var sensor := {"contract":transfer.control.version,"units":"SI","sequence":sensor_sequence,"timestamp_s":t,
		"joint_names":transfer.control.encoder_joint_names,"positions_rad":positions,"velocities_rad_s":velocities,
		"gyro_body_rad_s":[gyro.x,gyro.y,gyro.z],"gravity_body_unit":[gravity.x,gravity.y,gravity.z]}
	udp.put_packet(JSON.stringify(sensor).to_utf8_buffer())
	var deadline := Time.get_ticks_usec()+500000
	while udp.get_available_packet_count()==0 and Time.get_ticks_usec()<deadline:OS.delay_usec(500)
	if udp.get_available_packet_count()==0:push_error("Controller response watchdog expired");return false
	var action=JSON.parse_string(udp.get_packet().get_string_from_utf8())
	if not action is Dictionary or action.get("contract","")!=transfer.control.version or action.get("units","")!="SI":return false
	if action.get("sequence",-1)!=sensor_sequence or action.get("joint_names",[])!=transfer.control.encoder_joint_names:return false
	if absf(float(action.get("timestamp_s",-1))-t)>.000001:return false
	var validity := float(action.get("valid_for_s",0))
	if not is_finite(validity) or validity<=0 or validity>.1:return false
	var values=action.get("torque_Nm",[])
	if not values is Array or values.size()!=transfer.control.encoder_joint_names.size():return false
	for i in range(values.size()):
		if not typeof(values[i]) in [TYPE_FLOAT,TYPE_INT] or not is_finite(float(values[i])):return false
		var label: String=transfer.control.encoder_joint_names[i];var limit := 0.0
		for j in joint_records:
			if j.name==label:limit=float(j.torque_limit_Nm)
		if absf(float(values[i]))>limit+.000000001:return false
		external_torques[label]=float(values[i])
	if sensor_sequence<12:
		var errors: Dictionary={}
		var contacts: Dictionary={}
		for j in joint_records:
			if bool(j.actuated) and absf(float(states[j.name][0])-float(j.home))>.01:
				errors[j.name]=[rad_to_deg(float(states[j.name][0])-float(j.home)),
					float(states[j.name][1]),float(values[transfer.control.encoder_joint_names.find(j.name)])]
		for label in bodies:
			var others: Array=[]
			for other in bodies[label].get_colliding_bodies():others.append(other.name)
			if others.size():contacts[label]=others
		print(JSON.stringify({"diagnostic_sequence":sensor_sequence,"t":t,
			"root_m":[root.origin.x,-root.origin.z,root.origin.y],
			"torso_up":root.basis.y.dot(Vector3.UP),
			"max_joint_error_deg":rad_to_deg(max_joint_error),
			"max_loop_residual_mm":max_loop_residual*1000,"joint_errors_deg_and_torque":errors,
			"contacts":contacts}))
	action_expiry_s=t+validity;sensor_sequence+=1;return true

func _physics_process(delta: float) -> void:
	if bodies.is_empty():return
	if udp_enabled:
		if sample_count%torque_sample_steps==0 and not exchange_control():get_tree().quit(2);return
		if t>action_expiry_s:push_error("Motor action expired");get_tree().quit(2);return
	for j in joint_records:
		var state := measured_joint(j);var q: float=state[0];var v: float=state[1];var axis: Vector3=state[2]
		var force := -float(j.damping_SI)*v-float(j.stiffness_SI)*(q-float(j.spring_reference))
		if absf(v)>.00001:force-=float(j.friction_loss_SI)*signf(v)
		if bool(j.actuated):
			force+=float(external_torques.get(j.name,0)) if udp_enabled else float(j.kp)*(float(j.home)-q)-float(j.kd)*v+float(j.home_gravity_torque_Nm)
			# Above the declared motor speed, do not add driving torque in the
			# direction of motion. Opposing commanded torque remains available.
			if absf(v)>float(j.speed_limit_rad_s) and force*v>0:force=0
			if absf(force)>=float(j.torque_limit_Nm)-.000001:saturation_count+=1
			force=clampf(force,-float(j.torque_limit_Nm),float(j.torque_limit_Nm))
			max_joint_error=maxf(max_joint_error,absf(q-float(stance_targets[j.name])))
		var a: RigidBody3D=bodies[j.parent];var b: RigidBody3D=bodies[j.child]
		if String(j.type)=="slide":
			var pa: Vector3=a.global_transform*j.frame_a.origin;var pb: Vector3=b.global_transform*j.frame_b.origin
			a.apply_force(-axis*force*MASS_SCALE,pa-a.global_position);b.apply_force(axis*force*MASS_SCALE,pb-b.global_position)
		else:
			a.apply_torque(-axis*force*MASS_SCALE);b.apply_torque(axis*force*MASS_SCALE)
	var root := model_transform("torso")
	max_tilt=maxf(max_tilt,acos(clampf(root.basis.y.dot(Vector3.UP),-1,1)))
	for loop in transfer.constraints:
		var pa := model_transform(loop.body_a)*(C*vector(loop.point_a_local_m));var pb := model_transform(loop.body_b)*(C*vector(loop.point_b_local_m))
		max_loop_residual=maxf(max_loop_residual,pa.distance_to(pb))
	t+=delta;sample_count+=1
	if sample_count%200==0:trace.append({"t":t,"root_m":[root.origin.x,-root.origin.z,root.origin.y]})
	if t>=duration:
		var result := {"scope":"full free-base named standing pose; not walking/task acceptance", "engine":"Godot Jolt", "godot_version":Engine.get_version_info().string,"model_sha256":transfer.model_sha256,"mass_unit_scale":MASS_SCALE,"duration_s":t,"body_count":bodies.size(),"joint_count":joint_records.size(),"loop_count":transfer.constraints.size(),"root_displacement_m":root.origin.distance_to(root_start),"max_torso_tilt_deg":rad_to_deg(max_tilt),"max_joint_error_deg":rad_to_deg(max_joint_error),"max_loop_residual_mm":max_loop_residual*1000,"saturation_count":saturation_count,"samples":sample_count,"trace":trace,"inertia_frame":"principal COM; complete source inertia tensor preserved","root_free":true,"external_root_support":false}
		result.controller="shared_SI_UDP" if udp_enabled else "constant_home_gravity"
		result.pass=result.root_displacement_m<.02 and result.max_torso_tilt_deg<5 and result.max_joint_error_deg<5 and result.max_loop_residual_mm<.5
		var output := FileAccess.open("res://result.json",FileAccess.WRITE);output.store_string(JSON.stringify(result,"\t")+"\n");print(JSON.stringify(result))
		for rid in constraints:PhysicsServer3D.free_rid(rid)
		get_tree().quit(0 if result.pass else 2)
